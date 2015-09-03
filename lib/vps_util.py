from contextlib import contextmanager
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

auth_token_alphabet = string.letters + string.digits
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
    file("/srv/pillar/%s.sls" % name, 'w').write(
        pillar_tmpl % (random_auth_token(), name))

def trycmd(cmd, tries=sys.maxint):
    for x in xrange(tries):
        if not os.system(cmd):
            return True
        print "Command failed; retrying: %s" % cmd
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
            print "Rebooting..."
            trycmd(reboot_cmd)
            time.sleep(10)
            print "Fetching access data..."
            if trycmd(fetchaccessdata_cmd, 5):
                access_data = file('access_data.json').read()
                file('fallbacks.json', 'w').write("[" + access_data + "]")
                for tries in xrange(3):
                    out = subprocess.check_output(['checkfallbacks',
                                                   '-fallbacks', 'fallbacks.json',
                                                   '-connections', '1'])
                    if "[failed fallback check]" in out:
                        print "Fallback check failed; retrying..."
                    else:
                        print "VPS up!"
                        return yaml.load(access_data)
                    time.sleep(10)
            print "Minion seems to be misconfigured.  Let's try reapplying salt state..."
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
            | set(d['label'] for d in vultr_shell.server_list(None).itervalues()))
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
            for srv, cfg in cfgcache.get().iteritems()
            if yaml.load(cfg).values()[0]['addr'].split(':')[0] == ip]
    if srvs:
        redis_shell.hdel('cfgbysrv', *srvs)
        redis_shell.incr('srvcount')
    else:
        "No configs left to delete for %s." % name
    redis_shell.lrem(dc + ':vpss', name)
    redis_shell.incr(dc + ':vpss:version')

def vps_shell(lcs_name):
    if lcs_name.startswith('fp-nl'):
        import do_util
        return do_util
    elif lcs_name.startswith('fp-jp'):
        import vultr_util
        return vultr_util
    else:
        assert False, repr(lcs_name)

def destroy_vps(name):
    vps_shell(name).destroy_vps(name)