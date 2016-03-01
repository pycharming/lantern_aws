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

import redis_util
from redis_util import log2redis, nameipsrv, redis_shell
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
            # Sometimes our hammering interrupts dpkg such that highstate will
            # always fail to install any apt packages.
            trycmd("salt %s cmd.run 'dpkg --configure -a'" % name)
            trycmd("salt -t 1200 %s state.highstate" % name)

def cleanup_keys(do_shell=None, vultr_shell=None):
    vpss = all_vpss()
    ignore = set(["Accepted", "Unaccepted", "Rejected", "Keys:"])
    filter_out = vpss | ignore
    for key in subprocess.check_output(['salt-key', '-L']).split():
        if key not in filter_out:
            os.system('salt-key -d ' + key)

def srv_cfg_by_ip():
    ret = {}
    for srv, cfg in redis_shell.hgetall('srv->cfg').iteritems():
        ip = yaml.load(cfg).values()[0]['addr'].split(':')[0]
        if ip in ret:
            ret[ip][1].append(srv)
        else:
            ret[ip] = cfg, [srv]
    return ret

def retire_lcs(name,
               ip,
               # It's safe to cache this because a proxy will take at least 24h
               # since the time it's recycled (and thus new server IDs can be
               # entered for it) and the time it's destroyed. To be more
               # precise, 24h must elapse since the time it's been _split_. For
               # this to work, it's crucial to remove the
               # /home/lantern/server_split flag file whenever we recycle
               # proxies.
               byip=util.Cache(timeout=60*60,
                               update_fn=srv_cfg_by_ip)):
    cm = cm_by_name(name)
    region = region_by_name(name)
    srvs = byip.get().get(ip, (None, []))[1]
    txn = redis_shell.pipeline()
    if srvs:
        scores = [redis_shell.zscore(region + ':slices', srv) for srv in srvs]
        pairs = {"<empty:%s>" % int(score): score
                 for score in scores
                 if score}
        if pairs:
            txn.zadd(region + ":slices", **pairs)
            txn.zrem(region + ":slices", *srvs)
        txn.hdel('srv->cfg', *srvs)
        txn.incr('srvcount')
    else:
        print "No configs left to delete for %s." % name
    # Check whether this server is in the queue (because of recycling).
    for cfg in redis_shell.lrange(region + ':srvq', 0, -1):
        if cfg.split('|')[0] == ip:
            txn.lrem(region + ':srvq', cfg)
    txn.lrem(cm + ':vpss', name)
    txn.incr(cm + ':vpss:version')
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

def todaystr():
    now = datetime.utcnow()
    return "%d%02d%02d" % (now.year, now.month, now.day)

def my_cm():
    """
    The name of the cloudmaster managing me, excluding the 'cm-' prefix.
    """
    return os.getenv('CM')[3:]  # remove the "cm-" prefix

def cm_by_name(name):

    # Legacy.
    if name.startswith('fp-nl-'):
        name = name.replace('nl', 'doams3', 1)
    elif name.startswith('fp-jp-'):
        name = name.replace('jp', 'vltok1', 1)

    return name.split('-')[1]

def region_by_name(name):
    return region_by_dc(dc_by_name(name))

def my_region():
    return region_by_dc(dc_by_cm(my_cm()))

def dc_by_cm(cm):
    ret = cm[:6]
    assert ret in ['doams3', 'vltok1', 'dosgp1', 'vlfra1']
    return ret

def region_by_dc(dc):
    return {'doams3': 'etc',
            'vlfra1': 'etc',
            'dosgp1': 'sea',
            'vltok1': 'sea'}[dc]

def dc_by_name(name):
    return dc_by_cm(cm_by_name(name))

def access_data_to_cfg(access_data):
    ret = access_data.copy()
    ip = ret['addr'].split(':')[0]
    ret.update(pipeline=True,
               trusted=True,
               qos=10,
               weight=1000000)
    return "\n    " + yaml.dump({'fallback-' + ip: ret})

class vps:

    def __init__(self, name, ip, ram, provider, etc):
        self.name = name
        self.ip = ip
        self.ram = ram
        self.provider = provider
        self.etc = etc

    def __repr__(self):
        return "<%s (%s)>" % (self.name, self.ip)

def all_vpss():
    return (set(vps_shell('vl').all_vpss())
            | set(vps_shell('do').all_vpss()))

def retire_proxy(name=None, ip=None, srv=None, reason='failed checkfallbacks'):
    name, ip, srv = nameipsrv(name, ip, srv)
    p = redis_shell.pipeline()
    p.rpush(cm_by_name(name) + ':retireq', '%s|%s' % (name, ip))
    log2redis({'op': 'retire',
               'name': name,
               'ip': ip,
               'srv': srv,
               'reason': reason},
              pipeline=p)
    p.execute()
