#!/usr/bin/env python

import logging
import os

import psutil
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage


PIDFILE = "{{ lantern_pid }}"
INSTANCEID = "{{ pillar['instance_id'] }}"
IP = "{{ grains.get('ec2_public-ipv4', None) or grains['ipv4'][1] }}"
PORT = "{{ grains['proxy_port'] }}"
AWS_REGION = "{{ grains['aws_region'] }}"
CONTROLLER = "{{ grains['controller'] }}"
AWS_ID = "{{ pillar['aws_id'] }}"
AWS_KEY = "{{ pillar['aws_key'] }}"

aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}


def run():
    error = check_lantern()
    if error:
        logging.error(error)
        restart_lantern()
        report_error_to_controller(error)

def check_lantern():
    """
    Perform sanity checks to convince ourselves that one, and only one instance
    of Lantern is running.

    Return an error string if some of the above is not true, None otherwise.
    """
    try:
        pidstr = file(PIDFILE).read().strip()
    except IOError:
        return "no Lantern pid"
    try:
        pid = int(pidstr)
    except ValueError:
        return "invalid Lantern pid: %r" % pidstr
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return "no process for pid: %s" % pid
    if not parent.is_running():
        return "Lantern is not running"
    children = parent.get_children()
    if len(children) != 1:
        return "wrong number of children found: %s" % len(children)
    child = children[0]
    if child.name() != 'java':
        return "unexpected name for Lantern child process: %r" % child.name()
    if not child.is_running():
        return "Lantern child process not running"
    return check_pids('java', child.pid)

def check_pids(name, expected_pid):
    pids = [proc.pid for proc in psutil.process_iter()
            if proc.name() == name]
    # It's OK that there are other Java processes (e.g. install4j for building
    # wrappers.)
    if expected_pid in pids:
        return None
    else:
        return ("unexpected %r processes(es): we expected %r, but got %r"
                % (name, expected_pid, pids))

def restart_lantern():
    # We don't just use 'restart' because that will bail with an error unless
    # an existing lantern process is found.
    os.system("service lantern stop")
    os.system("service lantern start")

def report_error_to_controller(error):
    sqs = boto.sqs.connect_to_region(AWS_REGION, **aws_creds)
    ctrl_notify_q = sqs.get_queue("notify_%s" % CONTROLLER)
    msg = JSONMessage()
    # DRY: SQSChecker at lantern-controller.
    msg.set_body({'fp-alarm': error,
                  'instance-id': INSTANCEID,
                  'ip': IP,
                  'port': PORT,
                  'send-email': True})
    ctrl_notify_q.write(msg)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename='/home/lantern/check_lantern.log',
                        format='%(asctime)s %(levelname)-8s %(message)s')
    try:
        run()
    except Exception, e:
        logging.exception(e)
