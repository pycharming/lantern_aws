# This is a rather straightforward implementation of
#     http://oldblog.antirez.com/post/250

import os
import time

def read_local(filename):
    return file(os.path.join(os.path.dirname(__file__), filename)).read()

def now():
    # This only needs be consistent within the cloudmaster itself.
    return str(int(time.time()))

class Queue:

    def __init__(self, qname, redis_shell, timeout, sleep_time, check_done):
        self.qname = qname
        self.redis_shell = redis_shell
        self.timeout = timeout
        self.sleep_time = sleep_time
        self.check_done = check_done
        qread = redis_shell.register_script(read_local('qread.lua'))
        def read():
            return qread(keys=[self.qname], args=[now()])
        self._read = read
        qreplace = redis_shell.register_script(read_local('qreplace.lua'))
        def refresh(item):
            item_id = item.split('*')[0]
            qreplace(keys=[self.qname],
                     args=[item, item_id + "*" + now()])
        self._refresh = refresh

    def get_job(self):
        while True:
            item = self._read()
            if '*' in item:
                item_id, t = item.split('*')
            else:
                item_id = item
                t = None
            if item_id == "-1":
                time.sleep(self.sleep_time)
                continue
            if t is None:
                return item_id
            if time.time() - int(t) > self.timeout:
                if self.check_done(item_id):
                    self.redis_shell.lrem(self.qname, item, 1)
                else:
                    self._refresh(item)
                    return item_id
