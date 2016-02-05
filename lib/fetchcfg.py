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
# KEYS[3]: '<region>:bakedin-names'
# KEYS[4]: 'srvcount'
# KEYS[5]: '<region>:srvreqq'
# ARGV[1]: unix timestamp in seconds
luasrc = """
local cfg = redis.call("rpop", KEYS[1])
if not cfg then
    return "<no-servers-in-srvq>"
end
redis.call("lpush", KEYS[2], ARGV[1] .. "|" .. cfg)
local begin = string.find(cfg, "|")
local end_ = string.find(cfg, "|", begin + 1)
local name = string.sub(cfg, begin+1, end_-1)
redis.call("sadd", KEYS[3], name)
local serial = redis.call("incr", KEYS[4])
redis.call("lpush", KEYS[5], serial)
return cfg
"""

script = rs.register_script(luasrc)

def fetch(region):
    ipnamecfg = script(keys=[region + ':srvq',
                             region + ':bakedin',
                             region + ':bakedin-names',
                             'srvcount',
                             region + ':srvreqq'],
                       args=[int(time.time())])
    return ipnamecfg.split('|', 2)

def tojson(cfg):
    import yaml
    import json
    return json.dumps([yaml.load(cfg).values()[0]])

def extract_opts(args, *names):
    ret = {}
    for name in names:
        try:
            args.remove('--' + name)
            ret[name] = True
        except ValueError:
            ret[name] = False
    return ret

if __name__ == '__main__':
    args = sys.argv[:]
    opts = extract_opts(args, 'json', 'print-name-and-ip')
    region = None
    if len(args) == 1:
        region = rs.get('default-user-region')
    elif len(args) == 2:
        region = args[1]
    if not rs.sismember('user-regions', region):
        print "Usage: %s [--json] [--print-name-and-ip] [user-region]" % args[0]
        print "Where region must be one of 'sea' for Southeast Asia (currently, only China) or 'etc' (default) for anywhere else."
        print "Options (all default to false):"
        print "    --json: output a format that can be directly read by genconfig."
        print "    --print-name-and-ip: print name and ip of the new proxy, in addition to its config."
        sys.exit(1)
    ip, name, cfg = fetch(region)
    if opts['use_json']:
        cfg = tojson(cfg)
    if opts['print-name-and-ip']:
        print "\n%s (%s):\n" % (name, ip)
    print cfg
