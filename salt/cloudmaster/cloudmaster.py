#!/usr/bin/env python

from base64 import b64encode
from contextlib import contextmanager
from datetime import datetime
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

# Most cloud providers will allow longer instance names, but we are using
# this as the hostname in those machines too.  Hostnames longer than this
# may be problematic if we want to make FQDN names out of them.
MAX_INSTANCE_NAME_LENGTH = 64


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
    # DRY warning: FallbackProxyLauncher at lantern-controller.
    # TRANSITION: support old controllers for a while to make deployment less
    # time sensitive.
    userid = d.get('launch-fp-as', d.get('launch-invsrv-as'))
    if userid:
        # Backwards compatibility: we'll be getting serial numbers starting from 1
        # in the new fallback balancing scheme.  Just in case we get a new proxy
        # launch request from an old controller, let's mark it as 0.
        launch_proxy(userid,
                     d.get('launch-serial', 0),
                     d.get('launch-branch', 'fallback'),
                     d['launch-refrtok'],
                     msg)
    elif 'shutdown-fp' in d:
        instance_id = d['shutdown-fp']
        logging.info("Got shutdown request for %s" % instance_id)
        nproxies = shutdown_proxy(instance_id)
        if nproxies != 1:
            logging.error("Expected one proxy shut down, got %s" % nproxies)
        ctrl_req_q.delete_message(msg)
    else:
        logging.error("I don't understand this message: %s" % d)

def launch_proxy(email, serialno, branch, refresh_token, msg):
    logging.info("Got spawn request for '%s'" % clip_email(email))
    instance_name = create_instance_name(email, serialno)
    provider = get_provider()
    if shutdown_proxy(name_prefix(email, serialno)):
        # The Digital Ocean salt-cloud implementation will still find the
        # old instance if we try and recreate it too soon after deleting
        # it.
        logging.info("Waiting for the instance loss to sink in...")
        time.sleep(20)
    with proxy_map() as d:
        d[provider].append(
            {instance_name:
                {'minion': {'master': get_master_ip(provider)},
                 'grains': {'saltversion': SALT_VERSION,
                            'aws_region': AWS_REGION,
                            'controller': CONTROLLER,
                            'proxy_port': random.randint(1024, 61024),
                            'provider': provider,
                            'shell': '/bin/bash'}}})
    set_pillar(instance_name, email, branch, refresh_token, msg)
    #XXX: ugly, but we're already in sin running all this as a user with
    # passwordless sudo.  TODO: move this to a command with setuid or give
    # this user write access to /srv/pillar and to salt(-cloud) commands.
    os.system("sudo salt-cloud -y -m %s %s" % (MAP_FILE, REDIRECT))
    os.system("sudo salt %s state.highstate %s" % (instance_name, REDIRECT))

def shutdown_proxy(prefix):
    count = 0
    with proxy_map() as d:
        for provider in PROVIDERS:
            for entry in d[provider][:]:
                entry_name, = entry.keys()
                if entry_name.startswith(prefix):
                    logging.info("Found match in map.  Shutting it down...")
                    d[provider].remove(entry)
                    os.system("sudo salt-cloud -y -d %s %s" % (entry_name, REDIRECT))
                    count += 1
    return count

def set_pillar(instance_name, email, branch, refresh_token, msg):
    filename = '/home/lantern/%s.sls' % instance_name
    yaml.dump({
               'instance_id': instance_name,
               # DRY warning:
               # lantern_aws/salt/fallback_proxy/report_completion.py
               'user': email,
               'branch': branch,
               'refresh_token': refresh_token,
               'sqs_msg': b64encode(dumps(msg))},
              file(filename, 'w'))
    #XXX: ugly, but we're already in sin running all this as a user with
    # passwordless sudo.  TODO: move this to a command with setuid or give
    # this user write access to /srv/pillar and to salt(-cloud) commands.
    os.system("sudo mv %s /srv/pillar/" % filename)

@contextmanager
def proxy_map():
    d = load_map()
    yield d
    save_map(d)

def load_map():
    if os.path.exists(MAP_FILE):
        return yaml.load(file(MAP_FILE))
    else:
        return dict((p, []) for p in PROVIDERS)

def save_map(d):
    yaml.dump(d, file(MAP_FILE, 'w'))

def create_instance_name(email, serialno):
    now = datetime.now()
    return "%s%s-%s-%s" % (name_prefix(email, serialno),
                           now.year, now.month, now.day)

def find_instance_names(iterable, email, serialno):
    return [name for name in iterable
            if name.startswith(name_prefix(email, serialno))]

def name_prefix(email, serialno):
    sanitized_email = email.replace('@', '-at-').replace('.', '-dot-')
    # Since '-' is legal in e-mail usernames and domain names, and although
    # I don't imagine we'd approve problematic e-mails, let's be somewhat
    # paranoid and add some hash of the unsanitized e-mail to avoid clashes.
    sanitized_email += "-" + hex(hash(email))[-4:]
    # e-mail addresses can be up to 254 characters long!
    max_email_length = MAX_INSTANCE_NAME_LENGTH - len("-##-YYYY-MM-DD")
    if len(sanitized_email) > max_email_length:
        sanitized_email = "%x" % hash(email)
    return "fp-%s-%s-" % (sanitized_email, serialno)

def clip_email(email):
    at_index = email.find('@')
    return '%s...%s' % (email[:1], email[at_index-2:at_index])


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename=os.path.join(here, 'cloudmaster.log'),
                        format='%(asctime)s %(levelname)-8s %(message)s')
    check_q()
