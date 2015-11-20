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

# KEYS[1]: '<region>:srvq'
# KEYS[2]: '<region>:bakedin'
# KEYS[3]: 'srvcount'
# KEYS[4]: '<region>:srvreqq'
# ARGV[1]: unix timestamp in seconds
luasrc = """
local cfg = redis.call("rpop", KEYS[1])
if not cfg then
    return "<no-servers-in-srvq>"
end
redis.call("lpush", KEYS[2], ARGV[1] .. "|" .. cfg)
local serial = redis.call("incr", KEYS[3])
redis.call("lpush", KEYS[4], serial)
return cfg
"""

script = rs.register_script(luasrc)

def fetch(region):
    cfg = script(keys=[region + ':srvq',
                       region + ':bakedin',
                       'srvcount',
                       region + ':srvreqq'],
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
    region = None
    if len(args) == 1:
        region = rs.get('default-user-region')
    elif len(args) == 2:
        region = args[1]
    if not rs.sismember('user-regions', region):
        print "Usage: %s [--json] [user-region]" % args[0]
        print "Where region must be one of 'sea' for Southeast Asia (currently, only China) or 'etc' (default) for anywhere else."
        print "and use --json to output a format that can be directly read by genconfig."
        sys.exit(1)
    cfg = fetch(region)
    if use_json:
        cfg = tojson(cfg)
    print cfg
