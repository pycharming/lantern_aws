#!/usr/bin/env python

# This script checks whether Redis is available by pinging it and alerts on
# Slack if it isn't.
import sys
import os
import alert

redis_url = os.getenv('REDIS_URL')
redis_host = redis_url.split("@")[1]

def fail(msg):
    redis_url = os.getenv('REDIS_URL')
    redis_host = redis_url.split("@")[1]
    alert.send_to_slack("Redis Unavailable",
                        msg,
                        color="#ff0000",
                        channel="#redis-alerts")

try:
    from redis_util import redis_shell
    if redis_shell.ping():
        print "Redis is Up!"
    else:
        msg = "Redis at %s did not respond to ping" % redis_host
        fail(msg)
except Exception,e:
    msg = "Unable to check whether redis at %s is available: %s" % (redis_host, e)
    fail(msg)
