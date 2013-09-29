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
    # DRY warning: ShutdownProxy at lantern-controller.
    elif 'shutdown-proxy-for' in d:
        shutdown_proxy(d['shutdown-proxy-for'])
    else:
        assert 'feed-token-for' in d
        feed_token(d['feed-token-for'], d['feed-refrtok'], msg)


def launch_proxy(email, refresh_token, msg):
    logging.info("Got spawn request for '%s'" % clip_email(email))
    shutdown_proxy(email)
    instance_name = create_instance_name(email)
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
    os.system("sudo salt-cloud -y -m %s %s" % (MAP_FILE, REDIRECT))
    os.system("sudo salt %s state.highstate %s" % (instance_name, REDIRECT))

def shutdown_proxy(email):
    proxyname = pop_instance_name(email)
    if proxyname:
        logging.info("Deleting proxy for %s" % clip_email(email))
        delete_from_map(proxyname)
        os.system("sudo salt-cloud -y -d %s %s" % (proxyname, REDIRECT))
    else:
        logging.info("%s has no proxy to shut down" % clip_email(email))

def delete_from_map(instance):
    d = load_map()
    any_changes = False
    for provider, entries in d.iteritems():
        for entry in entries[:]:
            k, = entry.iterkeys()
            if k == instance:
                any_changes = True
                entries.remove(entry)
    if any_changes:
        yaml.dump(d, file(MAP_FILE, 'w'))

def feed_token(email, token, msg):
    logging.info("Got request to feed token to '%s'" % clip_email(email))
    set_pillar(email, token, email, 'setup_complete', msg)
    instance = get_instance_name(email)

    #XXX: ugly, but we're already in sin running all this as a user with
    # passwordless sudo.  TODO: move this to a command with setuid or give
    # this user write access to /srv/pillar and to salt(-cloud) commands.
    os.system("sudo salt %s cmd.run 'rm /home/lantern/reported_completion' %s"
              % (instance, REDIRECT))
    os.system("sudo salt %s state.highstate %s" % (instance, REDIRECT))

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

def load_map():
    if os.path.exists(MAP_FILE):
        return yaml.load(file(MAP_FILE))
    else:
        return dict((p, []) for p in PROVIDERS)

def save_map(d):
    yaml.dump(d, file(MAP_FILE, 'w'))

def load_instances():
    try:
        return yaml.load(file(INSTANCES_FILENAME))
    except IOError:
        return {}

def save_instances(d):
    yaml.dump(d, file(INSTANCES_FILENAME, 'w'))


def get_instance_name(email):
    return load_instances().get(email)

def create_instance_name(email):
    d = load_instances()
    assert email not in d
    s = set(d.itervalues())
    while True:
        name = (FALLBACK_PROXY_PREFIX
                + random_string(INSTANCE_NAME_ALPHABET, INSTANCE_NAME_LENGTH))
        if name not in s:
            break
    d[email] = name
    save_instances(d)
    return name

def pop_instance_name(email):
    d = load_instances()
    try:
        ret = d.pop(email)
        save_instances(d)
        return ret
    except KeyError:
        return None

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
