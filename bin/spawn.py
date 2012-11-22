#!/usr/bin/env python

# End-to-end script to launch one lantern instance.


import os
import sys
import time

import boto

import launch_stack
import init_lantern_peer
import update_node

try:
    _, stack_name, client_secrets, user_credentials = sys.argv
except ValueError:
    print "Usage: %s <name> <client-secrets> <user-credentials>" % sys.argv[0]
    sys.exit(0)

conn = boto.connect_cloudformation()

print "Launching stack..."
stack_id = launch_stack.run(stack_name, conn)

print "Waiting for stack to be created..."
while True:
    time.sleep(20)
    stack, = conn.describe_stacks(stack_id)
    if stack.stack_status == 'CREATE_COMPLETE':
        break
    print "(Still waiting...)"

ip = init_lantern_peer.get_ip(stack.list_resources())

print "Waiting for instance to be bootstrapped..."
while True:
    time.sleep(20)
    if not os.system("ssh -o 'StrictHostKeyChecking no' lantern@%s 'rm .bootstrap-done' 2> /dev/null" % ip):
        break
    print "(Still waiting...)"

print "Configuring instance..."
init_lantern_peer.run(stack_name, client_secrets, user_credentials)

print "Installing lantern and dependencies..."
update_node.run(ip)

print "Waiting for lantern to be built and launched..."
print "(This may take a while!)"
while True:
    time.sleep(60)
    if not os.system("ssh lantern@%s 'rm .update-done' 2> /dev/null" % ip):
        break
    print "(Still waiting...)"

print "Done! IP:", ip
