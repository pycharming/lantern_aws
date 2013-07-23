#!/usr/bin/env python

from base64 import b64encode
from cPickle import dumps
import json
import logging
import os
import random
import sys
import time
from functools import wraps

from lockfile import LockFile
import boto
import boto.ec2
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage
import yaml


here = os.path.dirname(sys.argv[0]) if __name__ == '__main__' else __file__


PRIVATE_IP = "{{ grains['ipv4'][0] }}"
#DRY warning: ../top.sls
FALLBACK_PROXY_PREFIX = "fp-"
MAP_FILE = '/home/lantern/map'
AWS_REGION = "{{ grains['aws_region'] }}"
AWS_ID = "{{ grains['aws_id'] }}"
AWS_KEY = "{{ grains['aws_key'] }}"
CONTROLLER = "{{ grains['controller'] }}"
SALT_VERSION = "{{ grains['saltversion'] }}"
aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}


def log_exceptions(f):
    @wraps(f)
    def deco(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception, e:
            logging.exception(e)
            raise
    return deco

@log_exceptions
def check_q():
    now = time.time()
    with LockFile(MAP_FILE):
        if time.time() - now > 60:
            logging.info("Took too long to acquire lock; letting go...")
            return
        actually_check_q()

def actually_check_q():
    logging.info("Checking queue...")
    sqs = boto.sqs.connect_to_region(AWS_REGION, **aws_creds)
    ctrl_req_q = sqs.get_queue("%s_request" % CONTROLLER)
    ctrl_req_q.set_message_class(JSONMessage)
    msg = ctrl_req_q.read()
    if msg is None:
        logging.info("Nothing in request queue.")
        return
    d = msg.get_body()
    # DRY warning: InvitedServerLauncher at lantern-controller.
    email = d['launch-invsrv-as']
    refresh_token = d['launch-refrtok']
    logging.info("Got spawn request for '%s'"
                 % clip_email(email))
    instance_name = "%s%x" % (FALLBACK_PROXY_PREFIX, hash(email))
    if get_ip(instance_name):
        logging.info("Instance %s already exists; killing..."
                     % instance_name)
        os.system("sudo salt-cloud -y -d %s >> /home/lantern/cloudmaster.log 2>&1" % instance_name)
        time.sleep(5)
    if get_ip(instance_name):
        logging.warning("Couldn't kill instance! Giving up.")
        return
    logging.info("Spawning %s..." % instance_name)
    if os.path.exists(MAP_FILE):
        d = yaml.load(file(MAP_FILE))
    else:
        d = {'aws': []}
    for entry in d['aws'][:]:
        if instance_name in entry:
            d['aws'].remove(entry)
    d['aws'].append({instance_name:
                     {'minion': {'master': PRIVATE_IP},
                      'grains': {'saltversion': SALT_VERSION,
                                 'userid': email,
                                 'refresh_token': refresh_token,
                                 'aws_region': AWS_REGION,
                                 'aws_id': AWS_ID,
                                 'aws_key': AWS_KEY,
                                 'controller': CONTROLLER,
                                 'proxy_port': random.randint(1024, 61024),
                                 'sqs_msg': b64encode(dumps(msg)),
                                 'shell': '/bin/bash'}}})
    yaml.dump(d, file(MAP_FILE, 'w'))
    os.system("sudo salt-cloud -y -m %s >> /home/lantern/cloudmaster.log 2>&1"
              % MAP_FILE)

def get_ip(instance_name):
    reservations = connect().get_all_instances(
            filters={'tag:Name': instance_name})
    if not reservations:
        return None
    instance, = reservations[0].instances
    return instance.ip_address

#XXX: refactor somewhere that we can share between machines.
def memoized(f):
    d = {}
    @wraps(f)
    def deco(*args):
        try:
            return d[args]
        except KeyError:
            ret = d[args] = f(*args)
            return ret
    return deco

@memoized
def connect():
    return boto.ec2.connect_to_region(AWS_REGION, **aws_creds)

def clip_email(email):
    at_index = email.find('@')
    return '%s...%s' % (email[:1], email[at_index-2:at_index])


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename=os.path.join(here, 'cloudmaster.log'),
                        format='%(levelname)-8s %(message)s')
    check_q()
