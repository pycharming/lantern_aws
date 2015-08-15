# This is a rather straightforward implementation of
#     http://oldblog.antirez.com/post/250

import os
import time

# KEYS[1]: name of the queue to use.
# ARGV[1]: current unix timestamp.
qread_src = """
local item = redis.call("rpop", KEYS[1])
local new
if string.find(item, "*") then
  new = item
else
  new = item .. "*" .. ARGV[1]
end
redis.call("lpush", KEYS[1], new)
return {item, new}
"""

# KEYS[1]: name of the queue to use
# ARGV[1]: name of the old item
# ARGV[2]: name of the new item
qreplace_src = """
redis.call("lrem", KEYS[1], 1, ARGV[1])
redis.call("lpush", KEYS[1], ARGV[2])
"""

def now():
    # This only needs be consistent within the cloudmaster itself.
    return str(int(time.time()))

class Queue:

    def __init__(self, qname, redis_shell, timeout):
        self.qname = qname
        self.redis_shell = redis_shell
        self.timeout = timeout
        qread = redis_shell.register_script(qread_src)
        def read():
            return qread(keys=[self.qname], args=[now()])
        self._read = read
        qreplace = redis_shell.register_script(qreplace_src)
        def refresh(item):
            item_id = item.split('*')[0]
            new_item = item_id + "*" + now()
            qreplace(keys=[self.qname],
                     args=[item, new_item])
            return new_item
        self._refresh = refresh

    def next_job(self):
        while True:
            item, new = self._read()
            if '*' in item:
                item_id, t = item.split('*')
            else:
                item_id = item
                t = None
            if item_id == "-1":
                return None, None
            expired = t and (time.time() - int(t) > self.timeout)
            if expired:
                new = self._refresh(new)
            if t is None or expired:
                def unregister():
                    print "Unregistering", repr(new)
                    self.redis_shell.lrem(self.qname, new, 1)
                return item_id, unregister
