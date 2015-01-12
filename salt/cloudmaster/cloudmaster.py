#!/usr/bin/env python

from base64 import b64encode
from contextlib import contextmanager
from datetime import datetime
from cPickle import dumps
import json
import logging
import os
from random import SystemRandom
import string
import sys
import time
from functools import wraps

from lockfile import LockFile
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage
import yaml

{% from 'ip.sls' import external_ip %}

random = SystemRandom()
here = os.path.dirname(sys.argv[0]) if __name__ == '__main__' else __file__


PUBLIC_IP = "{{ external_ip(grains) }}"
#DRY warning: ../top.sls
MAP_FILE = '/home/lantern/map'
AWS_REGION = "{{ grains['aws_region'] }}"
AWS_ID = "{{ pillar['aws_id'] }}"
AWS_KEY = "{{ pillar['aws_key'] }}"
CONTROLLER = "{{ grains['controller'] }}"
PRODUCTION_CONTROLLER = "{{ grains['production_controller'] }}"
SALT_VERSION = "{{ pillar['salt_version'] }}"
aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}
PROFILES = ['aws', 'do', 'do_sg_2GB', 'azure_sea_xs']
REDIRECT = " >> /home/lantern/cloudmaster.log 2>&1 "
SALT_PATH = '/usr/local/bin/salt'
SALT_CLOUD_PATH = '/usr/local/bin/salt-cloud'
SALT_KEY_PATH = '/usr/local/bin/salt-key'
DEFAULT_PROFILE = "{{ pillar['default_profile'] }}"

# Most cloud providers will allow longer instance names, but we are using
# this as the hostname in those machines too.  Hostnames longer than this
# may be problematic if we want to make FQDN names out of them.
MAX_INSTANCE_NAME_LENGTH = 64

AUTH_TOKEN_ALPHABET = string.letters + string.digits
AUTH_TOKEN_LENGTH = 64


def get_profile(sqs_msg):
    return sqs_msg.get_body().get('profile', DEFAULT_PROFILE)

def log_exceptions(f):
    @wraps(f)
    def deco(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception as e:
            log.exception(e)
            raise
    return deco

def check_q():
    now = time.time()
    with LockFile(MAP_FILE):
        if time.time() - now > 60:
            log.info("Took too long to acquire lock; letting go...")
            return
        try:
            actually_check_q()
        except:
            pass

@log_exceptions
def actually_check_q():
    log.info("Checking queue...")
    sqs = boto.sqs.connect_to_region(AWS_REGION, **aws_creds)
    ctrl_req_q = sqs.get_queue("%s_request" % CONTROLLER)
    ctrl_req_q.set_message_class(JSONMessage)
    msg = ctrl_req_q.read()
    if msg is None:
        log.info("Nothing in request queue.")
        return
    d = msg.get_body()
    # DRY warning: FallbackProxyLauncher at lantern-controller.
    if 'launch-fp-as' in d:
        userid = d['launch-fp-as']
        # Lantern won't start without *some* refresh token.  If we don't get one
        # from the controller let's just make up a bogus one.
        refresh_token = d.get('launch-refrtok', '').strip() or 'bogus'
        # Backwards compatibility: we'll be getting serial numbers starting
        # from 1 in the new fallback balancing scheme.  Just in case we get
        # a new proxy launch request from an old controller, let's mark it as
        # 0.
        serial = d.get('launch-serial', 0)
        # Salt scripts consuming these should use backwards-compatible defaults.
        pillars = d.get('launch-pillars', {})
        # Default proxy_protocol to tcp
        pillars.setdefault('proxy_protocol', 'tcp')
        # Make new fallbacks install from git by default.  We can't do this in
        # the fallback Salt config because there the defaults need to be
        # backwards compatible with old-style fallbacks.  We can't upgrade
        # those until we EOL old clients, since the new style of fallback
        # requires an auth token, that old fallbacks don't know to provide.
        pillars.setdefault('install-from', 'git')
        if 'auth_token' not in pillars:
            pillars['auth_token'] = random_auth_token()
        launch_fp(userid,
                  serial,
                  refresh_token,
                  msg,
                  pillars)
    elif 'shutdown-fp' in d:
        shutdown_one(d['shutdown-fp'])
        ctrl_req_q.delete_message(msg)
    elif 'shutdown-fl' in d:
        shutdown_one(d['shutdown-fl'])
        ctrl_req_q.delete_message(msg)
    elif 'launch-fl' in d:
        launch('fl', msg)
        ctrl_req_q.delete_message(msg)
    elif 'launch-wd' in d:
        launch('wd', msg)
        ctrl_req_q.delete_message(msg)
    else:
        log.error("I don't understand this message: %s" % d)

def launch_fp(email, serialno, refresh_token, msg, pillars):
    log.info("Got spawn request for '%s'" % clip_email(email))
    instance_name = create_instance_name(email, serialno)
    profile = get_profile(msg)
    if shutdown(name_prefix(email, serialno)):
        # The Digital Ocean salt-cloud implementation will still find the
        # old instance if we try and recreate it too soon after deleting
        # it.
        log.info("Waiting for the instance loss to sink in...")
        time.sleep(20)
    with instance_map() as d:
        proxy_port = (62443 if pillars['proxy_protocol'] == 'tcp'
                      else random.randint(1024, 61024))
        d[profile].append(
            {instance_name:
                {'minion': {'master': PUBLIC_IP},
                 'grains': {'saltversion': SALT_VERSION,
                            'aws_region': AWS_REGION,
                            'controller': CONTROLLER,
                            'production_controller': PRODUCTION_CONTROLLER,
                            'proxy_port': proxy_port,
                            'shell': '/bin/bash'}}})
    set_fp_pillar(instance_name, email, refresh_token, msg, pillars)
    apply_map()
    highstate(id)

def apply_map():
    os.system("%s -y -m %s %s" % (SALT_CLOUD_PATH, MAP_FILE, REDIRECT))

def actually_launch(id):
    # The first highstate may mess with the salt-minion service, so we want to
    # run it out of the salt-minion itself.
    os.system("%s %s cmd.run 'nohup bash -c \"salt-call state.highstate && reboot \" &' %s"
              % (SALT_PATH, id, REDIRECT))

def launch(instance_type, msg):
    it = instance_type
    log.info("Got launch request for '%s' instance" % it)
    profile = get_profile(msg)
    id = msg.get_body()['launch-%s' % it]
    if not id.startswith("%s-" % it):
        log.error("Expected id starting with '%s-'" % it)
        return
    log.info("Got spawn request for '%s'" % id)
    if shutdown(id):
        # The Digital Ocean salt-cloud implementation will still find the
        # old instance if we try and recreate it too soon after deleting
        # it.
        log.info("Waiting for the instance loss to sink in...")
        time.sleep(20)
    with instance_map() as d:
        d[profile].append(
            {id:
                {'minion': {'master': PUBLIC_IP},
                 'grains': {'saltversion': SALT_VERSION,
                            'aws_region': AWS_REGION,
                            'controller': CONTROLLER,
                            'production_controller': PRODUCTION_CONTROLLER,
                            'shell': '/bin/bash'}}})
    set_pillar(id, {})
    apply_map()
    highstate(id)

def shutdown_one(instance_id):
    log.info("Got shutdown request for %s" % instance_id)
    n = shutdown(instance_id)
    if n != 1:
        log.error("Expected one instance shut down, got %s" % n)

def shutdown(prefix):
    count = 0
    with instance_map() as d:
        for profile in d:
            for entry in d[profile][:]:
                entry_name, = entry.keys()
                if entry_name.startswith(prefix):
                    log.info("Found match in map.  Shutting it down...")
                    d[profile].remove(entry)
                    os.system("%s -y -d %s %s" % (SALT_CLOUD_PATH, entry_name, REDIRECT))
                    # salt-cloud should have done this, but as of this writing
                    # (2014-06-12) there is what seems like a temporary
                    # condition in Digital Ocean that causes salt-cloud to
                    # crash after it has successfully destroyed the droplet,
                    # but before it went on to delete its key from the salt
                    # master.
                    os.system("%s -y -d %s %s" % (SALT_KEY_PATH, entry_name, REDIRECT))
                    count += 1
    return count

def set_fp_pillar(instance_name, email, refresh_token, msg, extra_pillars):
    d = {'refresh_token': refresh_token,
         'user': email,
         'sqs_msg': encode_sqs_msg(msg)}
    d.update(extra_pillars)
    set_pillar(instance_name, d)

def encode_sqs_msg(msg):
    # DRY warning:
    # lantern_aws/salt/fallback_proxy/report_completion.py
    return b64encode(dumps(msg))

def set_pillar(instance_id, extra_pillars):
    filename = '/srv/pillar/%s.sls' % instance_id
    yaml.dump(dict(instance_id=instance_id,  # XXX: redundant; see grain 'id'
                   **extra_pillars),
              file(filename, 'w'))

@contextmanager
def instance_map():
    d = load_map(MAP_FILE)
    yield d
    save_map(MAP_FILE, d)

def load_map(filename):
    if os.path.exists(filename):
        ret = yaml.load(file(filename))
    else:
        ret = {}
    for p in PROFILES:
        if p not in ret:
            ret[p] = []
    return ret

def save_map(filename, d):
    yaml.dump(d, file(filename, 'w'))

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

def random_auth_token():
    return ''.join(random.choice(AUTH_TOKEN_ALPHABET)
                   for _ in xrange(AUTH_TOKEN_LENGTH))

if __name__ == '__main__':
    # I have to do all this crap because salt hijacks the root logger.
    log = logging.getLogger('cloudmaster')
    log.setLevel(logging.INFO)
    handler = logging.FileHandler(os.path.join(here, "cloudmaster.log"))
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
    log.addHandler(handler)
    log.info("cloudmaster starting...")
    check_q()
    log.info("cloudmaster done.")
