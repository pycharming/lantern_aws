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


PRIVATE_IP = "{{ grains['ec2_local-ipv4'] }}"
PUBLIC_IP = "{{ grains['ec2_public-ipv4'] }}"
#DRY warning: ../top.sls
FALLBACK_PROXY_PREFIX = "fp-"
MAP_FILE = '/home/lantern/map'
AWS_REGION = "{{ grains['aws_region'] }}"
AWS_ID = "{{ grains['aws_id'] }}"
AWS_KEY = "{{ grains['aws_key'] }}"
CONTROLLER = "{{ grains['controller'] }}"
SALT_VERSION = "{{ pillar['salt_version'] }}"
aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}

def get_provider():
    return 'do'

def get_master_ip(provider):
    return {'aws': PRIVATE_IP, 'do': PUBLIC_IP}[provider]

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
    if 'launch-invsrv-as' in d:
        launch_proxy(d['launch-invsrv-as'], d['launch-refrtok'], msg)
    else:
        assert 'feed-token-for' in d
        feed_token(d['feed-token-for'], d['feed-refrtok'], msg)

def launch_proxy(email, refresh_token, msg):
    logging.info("Got spawn request for '%s'" % clip_email(email))
    instance_name = get_instance_name(email)
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
        d = {'aws': [], 'do': []}
    for provider in ['aws', 'do']:
        for entry in d[provider][:]:
            if instance_name in entry:
                d[provider].remove(entry)
    d[get_provider()].append({instance_name:
                       {'minion': {'master': get_master_ip(get_provider())},
                        'grains': {'saltversion': SALT_VERSION,
                                   'aws_region': AWS_REGION,
                                   'aws_id': AWS_ID,
                                   'aws_key': AWS_KEY,
                                   'controller': CONTROLLER,
                                   'proxy_port': random.randint(1024, 61024),
                                   'shell': '/bin/bash'}}})
    yaml.dump(d, file(MAP_FILE, 'w'))
    # DRY warning: ProcessDonation at lantern-controller.
    if refresh_token == '<tokenless-donor>':
        runas_email = 'lanterndonors@gmail.com'
        refresh_token = '{{ pillar["lanterndonors_refrtok"] }}'
        # DRY warning: InvitedServerLauncher.py at lantern-controller.
        report_status = 'awaiting_token'
    else:
        runas_email = email
        # DRY warning: InvitedServerLauncher.py at lantern-controller.
        report_status = 'setup_complete'
    set_pillar(runas_email, refresh_token, email, report_status, msg)
    #XXX: ugly, but we're already in sin running all this as a user with
    # passwordless sudo.  TODO: move this to a command with setuid or give
    # this user write access to /srv/pillar and to salt(-cloud) commands.
    os.system("sudo salt-cloud -y -m %s >> /home/lantern/cloudmaster.log 2>&1"
              % MAP_FILE)

def feed_token(email, token, msg):
    logging.info("Got request to feed token to '%s'" % clip_email(email))
    set_pillar(email, token, email, 'setup_complete', msg)
    instance = get_instance_name(email)

    #XXX: ugly, but we're already in sin running all this as a user with
    # passwordless sudo.  TODO: move this to a command with setuid or give
    # this user write access to /srv/pillar and to salt(-cloud) commands.
    os.system("sudo salt %s cmd.run 'rm /home/lantern/reported_completion'"
              % instance)
    os.system("sudo salt %s state.highstate" % instance)

def set_pillar(runas_email, refresh_token, report_email, report_status, msg):
    filename = '/home/lantern/%s.sls' % get_instance_name(report_email)
    yaml.dump({
               # DRY warning:
               # lantern_aws/salt/fallback_proxy/report_completion.py
               'report_user': report_email,
               'report_status': report_status,
               # DRY warning:
               # lantern_aws/salt/fallback_proxy/user_credentials.json
               'run_as_user': runas_email,
               'refresh_token': refresh_token,
               'sqs_msg': b64encode(dumps(msg))},
              file(filename, 'w'))
    #XXX: ugly, but we're already in sin running all this as a user with
    # passwordless sudo.  TODO: move this to a command with setuid or give
    # this user write access to /srv/pillar and to salt(-cloud) commands.
    os.system("sudo mv %s /srv/pillar/" % filename)

def get_instance_name(email):
    return "%s%x" % (FALLBACK_PROXY_PREFIX, hash(email))

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
