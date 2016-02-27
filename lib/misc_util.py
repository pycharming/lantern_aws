from functools import wraps
import re
import subprocess
import time


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

def ssh(ip, cmd):
    return subprocess.check_output(['ssh', '-o', 'StrictHostKeyChecking=no', 'lantern@' + ip, cmd])
