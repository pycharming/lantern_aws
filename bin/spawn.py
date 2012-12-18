#!/usr/bin/env python

# End-to-end script to launch one lantern peer instance with installers.

import logging
import os
import sys
import time

import boto

import launch_stack
import init_files
import update_node


def run(stack_name, *filenames):

    conn = boto.connect_cloudformation()
    ip = None

    def loginfo(s):
        if ip is None:
            msg = "[spawn %s] %s" % (stack_name, s)
        else:
            msg = "[spawn %s @ %s ] %s" % (stack_name, ip, s)
        logging.info(msg)

    def wait_for_remote_file(desc, filename, check_interval):
        loginfo("Waiting for %s." % desc)
        time.sleep(check_interval * 2)
        while os.system(
            "ssh -o 'StrictHostKeyChecking no' lantern@%s 'test -f %s'"
            % (ip, filename)):
            time.sleep(check_interval)

    loginfo("Launching stack.")
    stack_id = launch_stack.run('lantern-peer', stack_name, conn)

    loginfo("Waiting for stack to be created.")
    while True:
        time.sleep(20)
        stack, = conn.describe_stacks(stack_id)
        if stack.stack_status == 'CREATE_COMPLETE':
            break

    ip = init_files.get_ip(stack.list_resources())

    wait_for_remote_file("instance to be bootstraped", '.bootstrap-done', 20)

    loginfo("Sending configuration and secret files.")
    init_files.run('lantern-peer',
                   stack_name,
                   *filenames)

    loginfo("Installing lantern and dependencies.")
    update_node.run('lantern-peer', ip)

    wait_for_remote_file("installers to be built", '.installers-built', 60)
    wait_for_remote_file("lantern to be built and launched",
                         '.update-done',
                         60)

    loginfo("Instance is up and running.")


if __name__ == '__main__':
    expected_files = init_files.configs['lantern-peer']['expected_files']
    if len(sys.argv) != len(expected_files) + 2:
        print "Usage:", sys.argv[0], "<stack name>",
        print init_files.files_usage(expected_files)
        sys.exit(1)
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')
    run(*sys.argv[1:])
