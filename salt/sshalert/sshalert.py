#!/usr/bin/env python

import os
import sys

import alert
try:
    from redis_util import redis_shell
except ImportError:
    # sshalert is enabled on all vpss, some of which don't have redis_shell.
    redis_shell = None

ip = os.environ['SSH_CONNECTION'].split(' ')[0]
user = os.environ['USER']

whitelisted = redis_shell is not None and redis_shell.exists('sshalert-whitelist:%s' % ip)

if not whitelisted:
    alert.send_to_slack("SSH login", "User %s *logging in* from IP %s" % (user, ip))

original_cmd = os.getenv('SSH_ORIGINAL_COMMAND')
if original_cmd:
    ret = os.system(original_cmd)
else:
    ret = os.system(os.environ['SHELL'])

if not whitelisted:
    alert.send_to_slack("SSH logout", "User %s from IP %s logging out" % (user, ip), color="good")

sys.exit(ret)
