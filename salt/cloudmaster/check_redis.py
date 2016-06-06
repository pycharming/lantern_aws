#!/usr/bin/env python

# This script checks whether Redis is available by pinging it and alerts on
# Slack if it isn't.
import sys
import os
import alert
import datetime
import socket

# The below duplicates logic in redis_util in case we can't import redis_util.
redis_url = os.getenv('REDIS_URL')
redis_host = redis_url.split("@")[1]

def fail(msg):
    alert.send_to_slack("Redis Unavailable",
                        msg,
                        color="danger",
                        channel="#redis-alerts")

try:
    from redis_util import redis_shell
    if not redis_shell.ping():
        fail("Redis at %s did not respond to ping" % redis_host)
    else:
        try:
            redis_shell.hset("__last_checked_at", socket.gethostname(), datetime.datetime.now())
            print "Redis is Up!"
        except Exception,e:
            fail("Redis at %s did not allow write, may be a read-only slave: %v" % (redis_host, e))
            
except Exception,e:
    msg = "Unable to check whether redis at %s is available: %s" % (redis_host, e)
    fail(msg)
