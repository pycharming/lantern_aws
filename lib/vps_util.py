__all__ = ['save_pillar', 'trycmd', 'hammer_the_damn_thing_until_it_proxies', 'tempdir']


from contextlib import contextmanager
import json
import os
import random
import subprocess
import string
import sys
import tempfile
import time


pillar_tmpl = """\
controller: lanternctrl1-2
auth_token: %s
install-from: git
instance_id: %s
proxy_protocol: tcp
"""

auth_token_alphabet = string.letters + string.digits
auth_token_length = 64

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

def hammer_the_damn_thing_until_it_proxies(name, reboot_cmd, fetchaccessdata_cmd):
    with tempdir(name):
        while True:
            # Wait a bit to make sure highstate has started.
            print "Rebooting..."
            trycmd(reboot_cmd)
            time.sleep(10)
            print "Fetching access data..."
            if trycmd(fetchaccessdata_cmd, 10):
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
                        return json.loads(access_data)
                    time.sleep(10)
            print "Minion seems to be misconfigured.  Let's try reapplying salt state..."
            trycmd("salt -t 1800 %s state.highstate" % name)
