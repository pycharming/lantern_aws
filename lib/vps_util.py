from contextlib import contextmanager
from datetime import datetime
import os
import random
import re
import subprocess
import string
import sys
import tempfile
import time
import yaml

from redis_util import redis_shell
import misc_util as util


pillar_tmpl = """\
controller: lanternctrl1-2
auth_token: %s
install-from: git
instance_id: %s
proxy_protocol: tcp
"""

auth_token_alphabet = string.ascii_letters + string.digits
auth_token_length = 64

highstate_re = re.compile(r'The function "state.highstate" is running as PID (\d+)')

@contextmanager
def tempdir(id_):
    olddir = os.getcwd()
    workdir = tempfile.mkdtemp(prefix='init_vps_%s_' % id_)
    os.chdir(workdir)
    try:
        yield
    finally:
        os.chdir(olddir)
        os.system("rm -rf " + workdir)

def random_auth_token():
    return ''.join(random.choice(auth_token_alphabet)
                   for _ in xrange(auth_token_length))

def save_pillar(name):
    with file("/srv/pillar/%s.sls" % name, 'w') as f:
        f.write(pillar_tmpl % (random_auth_token(), name))

def trycmd(cmd, tries=sys.maxsize):
    for x in xrange(tries):
        if not os.system(cmd):
            return True
        print("Command failed; retrying: %s" % cmd)
        time.sleep(10)
    return False

def highstate_pid(name):
    out = subprocess.check_output(["salt", name, "state.running"])
    lines = out.strip().split('\n')
    if len(lines) > 1:
        match = highstate_re.search(lines[1])
        if match:
            return match.groups()[0]
    return None

# For good measure.
def hammer_the_damn_thing_until_it_proxies(name, ssh_tmpl, fetchaccessdata_cmd):
    reboot_cmd = ssh_tmpl % 'reboot'
    kill_tmpl = ssh_tmpl % 'kill -9 %s'
    with tempdir(name):
        while True:
            print("Rebooting...")
            trycmd(reboot_cmd)
            time.sleep(10)
            print("Fetching access data...")
            if trycmd(fetchaccessdata_cmd, 5):
                access_data = file('access_data.json').read()
                file('fallbacks.json', 'w').write("[" + access_data + "]")
                for tries in xrange(3):
                    out = subprocess.check_output(['checkfallbacks',
                                                   '-fallbacks', 'fallbacks.json',
                                                   '-connections', '1'])
                    if "[failed fallback check]" in out:
                        print("Fallback check failed; retrying...")
                    else:
                        print("VPS up!")
                        return yaml.load(access_data)
                    time.sleep(10)
            print("Minion seems to be misconfigured.  Let's try reapplying salt state...")
            pid = highstate_pid(name)
            if pid:
                trycmd(kill_tmpl % pid, 5)
            trycmd("salt -t 1800 %s state.highstate" % name)

def cleanup_keys(do_shell=None, vultr_shell=None):
    if do_shell is None:
        import do_util
        do_shell = do_util.do
    if vultr_shell is None:
        import vultr_util
        vultr_shell = vultr_util.vultr
    vpss = (set(d.name for d in do_shell.get_all_droplets())
            | set(d['label'] for d in vultr_shell.server_list(None).values()))
    ignore = set(["Accepted", "Unaccepted", "Rejected", "Keys:"])
    filter_out = vpss | ignore
    for key in subprocess.check_output(['salt-key', '-L']).split():
        if key not in filter_out:
            os.system('salt-key -d ' + key)

def retire_lcs(name,
               ip,
               cfgcache=util.Cache(timeout=60*60,
                                   update_fn=lambda: redis_shell.hgetall('cfgbysrv'))):
    if name.startswith('fp-jp-'):
        dc = 'vltok1'
    elif name.startswith('fp-nl-'):
        dc = 'doams3'
    else:
        assert False
    srvs = [srv
            for srv, cfg in cfgcache.get().items()
            if yaml.load(cfg).values()[0]['addr'].split(':')[0] == ip]
    txn = redis_shell.pipeline()
    if srvs:
        scores = [redis_shell.zscore(dc + ':slices', srv) for srv in srvs]
        pairs = {"<empty:%s>" % score: score
                 for score in scores
                 if score}
        if pairs:
            txn.zadd(dc + ":slices", **pairs)
            txn.zrem(dc + ":slices", *srvs)
        txn.hdel('cfgbysrv', *srvs)
        txn.incr('srvcount')
    else:
        print "No configs left to delete for %s." % name
    txn.lrem(dc + ':vpss', name)
    txn.incr(dc + ':vpss:version')
    txn.execute()

def vps_shell(provider_etc):
    """
    provider_etc is any string that starts with the provider ID.

    By convention, datacenter and cloudmaster IDs meet this condition.
    """
    if provider_etc.startswith('do'):
        import do_util
        return do_util
    elif provider_etc.startswith('vl'):
        import vultr_util
        return vultr_util
    else:
        assert False, repr(provider_etc)

def destroy_vps(name):
    vps_shell(dc_by_name(name)).destroy_vps(name)
    srv = redis_shell.hget('name->srv', name)
    if srv:
        txn = redis_shell.pipeline()
        txn.hdel('name->srv', name)
        txn.hdel('srv->name', srv)
        txn.execute()

def srv_cfg_by_ip():
    ret = {}
    for srv, cfg in redis_shell.hgetall('cfgbysrv').iteritems():
        ip = yaml.load(cfg).values()[0]['addr'].split(':')[0]
        if ip in ret:
            ret[ip][1].append(srv)
        else:
            ret[ip] = cfg, [srv]
    return ret

def todaystr():
    now = datetime.utcnow()
    return "%d%02d%02d" % (now.year, now.month, now.day)

def dc_by_name(name):

    # Legacy.
    if name.startswith('fp-nl-'):
        name = name.replace('nl', 'doams3', 1)
    elif name.startswith('fp-jp-'):
        name = name.replace('jp', 'vltok1', 1)

    ret = name[3:9]
    assert ret in ['doams3', 'vltok1', 'dosgp1']
    return ret

def cmid():
    "cloudmaster id"
    return os.getenv('CM')[3:]  # remove the "cm-" prefix

class vps:

    def __init__(self, name, ip, etc):
        self.name = name
        self.ip = ip
        self.etc = etc

    def __repr__(self):
        return "<%s (%s)>" % (self.name, self.ip)
