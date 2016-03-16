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

def ssh(ip, cmd, timeout=60):
    try:
        return subprocess.check_output(['timeout', str(timeout), 'ssh', '-o', 'StrictHostKeyChecking=no', 'lantern@' + ip, cmd])
    except subprocess.CalledProcessError as e:
        return ('CalledProcessError', e.returncode, e.output)
    except Exception as e:
        return traceback.format_exc()

def _single_arg_ssh(args):
    "Utility function for pssh; importable and taking a single argument."
    return ssh(*args)

def pssh(ips, cmd, timeout=60, pool=None):
    pool = pool or multiprocessing.Pool(min(len(ips), 50))
    return pool.map(_single_arg_ssh, ((ip, cmd, timeout) for ip in ips))

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
