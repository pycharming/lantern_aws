#!/usr/bin/env python

import os
import sys

import alert

ip = os.environ['SSH_CONNECTION'].split(' ')[0]
user = os.environ['USER']

alert.send_to_slack("SSH login", "User %s *logging in* from IP %s" % (user, ip))

original_cmd = os.getenv('SSH_ORIGINAL_COMMAND')
if original_cmd:
    ret = os.system(original_cmd)
else:
    ret = os.system(os.environ['SHELL'])

alert.send_to_slack("SSH logout", "User %s from IP %s logging out" % (user, ip), color="good")

sys.exit(ret)
