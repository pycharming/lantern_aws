#!/usr/bin/env python

import os
import redis
import sys

redis_url = os.getenv("REDIS_URL") or os.getenv("REDISCLOUD_PRODUCTION_URL")
if not redis_url:
    print "You need a REDIS_URL env variable.  Get the value at"
    print "https://github.com/getlantern/too-many-secrets/blob/master/lantern_aws/config_server.yaml#L2"
    sys.exit(1)
rs = redis.from_url(redis_url)

# KEYS[1]: '<dc>:srvq'
# KEYS[2]: '<dc>:bakedin'
# KEYS[3]: '<dc>:srvreqid'
# KEYS[4]: '<dc>:srvreqq'
luasrc = """
local cfg = redis.call("rpoplpush", KEYS[1], KEYS[2])
local serial = redis.call("incr", KEYS[3])
redis.call("lpush", KEYS[4], serial)
return cfg
"""

script = rs.register_script(luasrc)

def fetch(dc='doams3'):
    cfg = script(keys=[dc + ':srvq',
                       dc + ':bakedin',
                       dc + ':srvreqid',
                       dc + ':srvreqq'])
    return cfg.split('|', 1)[1]


if __name__ == '__main__':
    dc = None
    if len(sys.argv) == 1:
        dc = 'doams3'
    elif len(sys.argv) == 2:
        dc = sys.argv[1]
    if dc not in ['doams3', 'vltok1']:
        print "Usage: %s [datacenter]" % sys.argv[0]
        print "Where datacenter must be one of 'doams3' (for Amsterdam) or 'vltok1' (for Tokyo)"
        sys.exit(1)
    print fetch(dc)
