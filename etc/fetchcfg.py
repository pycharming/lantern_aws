#!/usr/bin/env python

import os
import redis
import sys
import time

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
# ARGV[1]: unix timestamp in seconds
luasrc = """
local cfg = redis.call("rpop", KEYS[1])
redis.call("lpush", KEYS[2], ARGV[1] .. "|" .. cfg)
local serial = redis.call("incr", KEYS[3])
redis.call("lpush", KEYS[4], serial)
return cfg
"""

script = rs.register_script(luasrc)

def fetch(dc='doams3'):
    cfg = script(keys=[dc + ':srvq',
                       dc + ':bakedin',
                       dc + ':srvreqid',
                       dc + ':srvreqq'],
                 args=[int(time.time())])
    return cfg.split('|', 1)[1]

def tojson(cfg):
    import yaml
    import json
    return json.dumps([yaml.load(cfg).values()[0]])


if __name__ == '__main__':
    args = sys.argv[:]
    try:
        args.remove('--json')
        use_json = True
    except ValueError:
        use_json = False
    dc = None
    if len(args) == 1:
        dc = 'doams3'
    elif len(args) == 2:
        dc = args[1]
    if dc not in ['doams3', 'vltok1']:
        print "Usage: %s [--json] [datacenter]" % args[0]
        print "Where datacenter must be one of 'doams3' (for Amsterdam, default) or 'vltok1' (for Tokyo)"
        print "and use --json to output a format that can be directly read by genconfig."
        sys.exit(1)
    cfg = fetch(dc)
    if use_json:
        cfg = tojson(cfg)
    print cfg
