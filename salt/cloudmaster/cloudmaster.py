#!/usr/bin/env python

from base64 import b64encode
from cPickle import dumps
import json
import logging
import os
import random
import string
import sys
import time
from functools import wraps

from lockfile import LockFile
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
AWS_ID = "{{ pillar['aws_id'] }}"
AWS_KEY = "{{ pillar['aws_key'] }}"
CONTROLLER = "{{ grains['controller'] }}"
SALT_VERSION = "{{ pillar['salt_version'] }}"
aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}
PROVIDERS = ['aws', 'do']
REDIRECT = " >> /home/lantern/cloudmaster.log 2>&1 "
INSTANCES_FILENAME = 'instance_names.yaml'

# We expect all cloud providers to accept any alphanumerics for instance names.
# We've had trouble with about every other character.
INSTANCE_NAME_ALPHABET = string.letters + string.digits
INSTANCE_NAME_LENGTH = 12


def get_provider():
    return 'aws'

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
    # DRY warning: FallbackProxyLauncher at lantern-controller.
    # TRANSITION: support old controllers for a while to make deployment less
    # time sensitive.
    userid = d.get('launch-fp-as', d.get('launch-invsrv-as'))
    launch_proxy(userid, d['launch-refrtok'], msg)

def launch_proxy(email, refresh_token, msg):
    logging.info("Got spawn request for '%s'" % clip_email(email))
    instance_name = create_instance_name()
    provider = get_provider()
    d = load_map()
    d[provider].append(
        {instance_name:
            {'minion': {'master': get_master_ip(provider)},
             'grains': {'saltversion': SALT_VERSION,
                        'aws_region': AWS_REGION,
                        'controller': CONTROLLER,
                        'proxy_port': random.randint(1024, 61024),
                        'provider': provider,
                        'shell': '/bin/bash'}}})
    save_map(d)
    set_pillar(instance_name, email, refresh_token, msg)
    #XXX: ugly, but we're already in sin running all this as a user with
    # passwordless sudo.  TODO: move this to a command with setuid or give
    # this user write access to /srv/pillar and to salt(-cloud) commands.
    os.system("sudo salt-cloud -y -m %s %s" % (MAP_FILE, REDIRECT))
    os.system("sudo salt %s state.highstate %s" % (instance_name, REDIRECT))

def set_pillar(instance_name, email, refresh_token, msg):
    filename = '/home/lantern/%s.sls' % instance_name
    yaml.dump({
               # DRY warning:
               # lantern_aws/salt/fallback_proxy/report_completion.py
               'user': email,
               'refresh_token': refresh_token,
               'sqs_msg': b64encode(dumps(msg))},
              file(filename, 'w'))
    #XXX: ugly, but we're already in sin running all this as a user with
    # passwordless sudo.  TODO: move this to a command with setuid or give
    # this user write access to /srv/pillar and to salt(-cloud) commands.
    os.system("sudo mv %s /srv/pillar/" % filename)

def load_map():
    if os.path.exists(MAP_FILE):
        return yaml.load(file(MAP_FILE))
    else:
        return dict((p, []) for p in PROVIDERS)

def save_map(d):
    yaml.dump(d, file(MAP_FILE, 'w'))

def load_instances():
    try:
        ret = yaml.load(file(INSTANCES_FILENAME))
        # Backwards compatibility; this used to be a dict.
        if isinstance(ret, dict):
            ret = ret.values()
        return ret
    except IOError:
        return []

def save_instances(l):
    yaml.dump(l, file(INSTANCES_FILENAME, 'w'))

def create_instance_name():
    l = load_instances()
    while True:
        name = (FALLBACK_PROXY_PREFIX
                + random_string(INSTANCE_NAME_ALPHABET, INSTANCE_NAME_LENGTH))
        if name not in l:
            break
    l.append(name)
    save_instances(l)
    return name

def clip_email(email):
    at_index = email.find('@')
    return '%s...%s' % (email[:1], email[at_index-2:at_index])

def random_string(alphabet, length):
    return "".join([random.choice(alphabet) for _ in xrange(length)])

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename=os.path.join(here, 'cloudmaster.log'),
                        format='%(levelname)-8s %(message)s')
    check_q()
