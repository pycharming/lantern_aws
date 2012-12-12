#!/usr/bin/env python

# End-to-end script to launch one lantern instance.


import os
import sys
import time

import boto

import launch_stack
import init_lantern_peer
import init_files
import update_node


if len(sys.argv) != len(init_lantern_peer.expected_files) + 2:
    print "Usage:", sys.argv[0], "<stack name>",
    print init_files.file_usage(init_lantern_peer.expected_files)
    sys.exit(0)

stack_name = sys.argv[1]

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

ip = init_files.get_ip(stack.list_resources())

print "Waiting for instance to be bootstrapped..."
while True:
    time.sleep(20)
    if not os.system("ssh -o 'StrictHostKeyChecking no' lantern@%s 'rm .bootstrap-done' 2> /dev/null" % ip):
        break
    print "(Still waiting...)"

print "Configuring instance..."
init_files.run('lantern',
               init_lantern_peer.expected_files,
               stack_name,
               *sys.argv[2:])

print "Installing lantern and dependencies..."
update_node.run(ip)

print "Waiting for installers to be built..."
print "(This may take a while!)"
while True:
    time.sleep(60)
    if not os.system("ssh lantern@%s 'cat .installers-built' > /dev/null 2>&1" % ip):
        break
    print "(Still waiting...)"

print "Waiting for lantern to be built and launched..."
print "(This may take a while!)"
while True:
    time.sleep(60)
    if not os.system("ssh lantern@%s 'rm .update-done' 2> /dev/null" % ip):
        break
    print "(Still waiting...)"

print "Done! IP:", ip
