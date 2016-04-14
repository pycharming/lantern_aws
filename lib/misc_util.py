from __future__ import division

from collections import defaultdict
from functools import wraps
import re
import multiprocessing
import subprocess
import time
import traceback


class Cache:
    def __init__(self, timeout, update_fn):
        self.timeout = timeout
        self.update_fn = update_fn
        self.last_update_time = 0
        self.contents = "UNINITIALIZED?!"
    def get(self):
        if time.time() - self.last_update_time > self.timeout:
            self.contents = self.update_fn()
            self.last_update_time = time.time()
        return self.contents

def memoized(f):
    d = {}
    @wraps(f)
    def deco(*args):
        try:
            return d[args]
        except KeyError:
            ret = d[args] = f(*args)
            return ret
    return deco

ipre = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
def scan_ips(txt):
    return set(ipre.findall(txt))

class obj(dict):
    def __getattr__(self, name):
        return self.__getitem__(name)
    def __setattr__(self, name, value):
        return self.__setitem__(name, value)

class defaultobj(defaultdict):
    def __getattr__(self, name):
        return self.__getitem__(name)
    def __setattr__(self, name, value):
        return self.__setitem__(name, value)

def ssh(ip, cmd, timeout=60, whitelist=True):
    if whitelist:
        whitelist_ssh()
    return cmd_error_and_output(
        with_timeout(['ssh', '-o', 'StrictHostKeyChecking=no', 'lantern@' + ip, cmd],
                     timeout))

def whitelist_ssh(time=60):
    try:
        from redis_util import redis_shell as redis_shell
    except ImportError:
        print >> sys.stderr, "No redis access; I won't be whitelisted in this SSH session"
        return
    ip = subprocess.check_output(['dig', '+short', 'myip.opendns.com', '@resolver1.opendns.com']).strip()
    redis_shell.setex('sshalert-whitelist:%s' % ip, 'admin', time)

def with_timeout(args, timeout=None):
    if timeout is None:
        return args
    else:
        return ['timeout', str(timeout)] + args

def cmd_error_and_output(args):
    try:
        return 0, subprocess.check_output(args)
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output
    except Exception as e:
        return 'python-exception', traceback.format_exc()

def _single_arg_ssh(args):
    "Utility function for pssh; importable and taking a single argument."
    return ssh(*args)

def pssh(ips, cmd, timeout=60, pool=None, whitelist=True):
    poolsize = min(len(ips), 50)
    if pool is None:
        pool = multiprocessing.Pool(poolsize)
    else:
        try:
            # This is unlikely to change in Python 2. All interface breaking
            # changes are happening in 3. If this does change the impact will
            # be minor (either some log noise or some whitelist entries lasting
            # longer).
            poolsize = max(1, int(pool._processes))
        except AttributeError:
            pass
    if whitelist:
        # Optimization: we do a single whitelist call instead of len(ips) ones.
        #
        # We set a conservative expiration for this one. The whole operation
        # should have concluded or timed out by this time.
        whitelist_ssh(time=60 + (timeout * len(ips) // poolsize))
    return pool.map(_single_arg_ssh, ((ip, cmd, timeout, False) for ip in ips))

def confirm(msg):
    while True:
        resp = raw_input(msg + " (y/N): ")
        if not resp or resp in 'nN':
            return False
        if resp in 'yY':
            return True
        print "*** Please enter 'y' or 'n'. ***"

def percent(part, whole):
    return "%.2f%%" % (part * 100 / whole)
