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


def run(stack_type, stack_name, *filenames, **kwargs):

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
            "ssh -o 'StrictHostKeyChecking no' lantern@%s 'test -f %s' 2>/dev/null"
            % (ip, filename)):
            time.sleep(check_interval)

    loginfo("Launching stack.")
    stack_id = launch_stack.run(stack_type, stack_name, conn)

    loginfo("Waiting for stack to be created.")
    while True:
        time.sleep(20)
        stack, = conn.describe_stacks(stack_id)
        if stack.stack_status == 'CREATE_COMPLETE':
            break

    ip = init_files.get_ip(stack.list_resources())

    # XXX: this is so the invsrvlauncher can trigger the building of the
    # instance ASAP.  This is ugly, but it was the least traumatic change that
    # I could think of.  All this is due to a big rewrite anyway.
    callback = kwargs.get('host_port_callback')
    if callback is not None:
        callback(ip, init_files.get_port(stack.list_resources()))

    wait_for_remote_file("instance to be bootstraped", '.bootstrap-done', 20)

    loginfo("Sending configuration and secret files.")
    init_files.run(stack_type,
                   stack_name,
                   *filenames)

    loginfo("Pushing salt configuration.")
    update_node.run(stack_type, ip)

    wait_for_remote_file("instance set up to complete",
                         '.update-done',
                         60)

    loginfo("Instance is up and running.")


if __name__ == '__main__':
    try:
        stack_type = sys.argv[1]
    except IndexError:
        print "Usage:", sys.argv[0], "<stack-type> <stack-name> [<required-file> ...]"
        sys.exit(1)

    expected_files = init_files.configs[stack_type]['expected_files']

    if len(sys.argv) != len(expected_files) + 3:
        print "Usage:", sys.argv[0], "<stack-type> <stack-name>",
        print init_files.files_usage(expected_files)
        sys.exit(1)
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')
    run(*sys.argv[1:])
