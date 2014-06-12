#!/usr/bin/env python

# XXX: refactor common functionality of this and
# ../fallback_proxy/check_lantern.py into a common check_service.py

import logging
import os

import psutil
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage


PIDFILE = "{{ wrapper_builder_pid }}"
IP = "{{ external_ip }}"
AWS_REGION = "{{ grains['aws_region'] }}"
CONTROLLER = "{{ grains['controller'] }}"
AWS_ID = "{{ pillar['aws_id'] }}"
AWS_KEY = "{{ pillar['aws_key'] }}"
LOGFILE = "/home/lantern/check_wrapper_builder.log"

SEP = "--------------------------------------------------"

aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}


def run():
    error = check_wrapper_builder()
    if error:

        # Log these unconditionally if we need to debug deaths.
        logCommand("top -b -n 1")
        logCommand("ps aux --sort -rss | head -10")
        logCommand("free -lm")
        logCommand("vmstat")

        logging.error(error)
        restart_wrapper_builder()
        report_error_to_controller(error)
    else:
        logging.info("all OK.")

def check_wrapper_builder():
    """
    Perform sanity checks to convince ourselves that one, and only one instance
    of the wrapper builder is running.

    Return an error string if some of the above is not true, None otherwise.
    """
    logging.info("checking wrapper builder...")
    try:
        pidstr = file(PIDFILE).read().strip()
    except IOError:
        return "no wrapper_builder pid"
    try:
        pid = int(pidstr)
    except ValueError:
        return "invalid wrapper_builder pid: %r" % pidstr

    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return "no process for pid: %s" % pid
    if not proc.is_running():
        return "wrapper_builder is not running"
    # Let's add this back if we need to debug wrapper builder deaths.
    #logCommand('cat /proc/%d/status' % proc.pid)
    for proc in psutil.process_iter():
        if proc.cmdline()[0:2] == ['python', 'wrapper_builder.py']:
            if proc.pid != pid:
                return ("unexpected additional build_wrappers process: expected %r, got %r"
                        % (pid, proc.pid))

def restart_wrapper_builder():
    # We don't just use 'restart' because that will bail with an error unless
    # an existing wrapper_builder process is found.
    os.system("service wrapper_builder stop >> %s 2>&1" % LOGFILE)
    os.system("service wrapper_builder start >> %s 2>&1" % LOGFILE)

def report_error_to_controller(error):
    sqs = boto.sqs.connect_to_region(AWS_REGION, **aws_creds)
    ctrl_notify_q = sqs.get_queue("notify_%s" % CONTROLLER)
    msg = JSONMessage()
    # DRY: SQSChecker at lantern-controller.
    msg.set_body({'fp-alarm': error,
                  'instance-id': '(wrapper builder)',
                  'ip': IP,
                  'port': 'n/a',
                  'send-email': True})
    ctrl_notify_q.write(msg)
    logging.info("reported error to controller")

def logCommand(cmd):
    logging.info(SEP + "\n")
    logging.info(cmd)
    os.system("%s >> %s" % (cmd, LOGFILE))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename=LOGFILE,
                        format='%(asctime)s %(levelname)-8s %(message)s')
    try:
        run()
    except:
        logging.exception("uncaught top-level exception")
