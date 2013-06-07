#!/usr/bin/env python

import json
import logging
from Queue import Empty  # for the queue.Queue.Empty exception.
from multiprocessing import Process, Queue
import os
import random
import string
import sys
import tempfile
import time
from functools import wraps

import boto
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage
from boto.exception import BotoServerError
from boto.s3.key import Key


here = os.path.dirname(sys.argv[0]) if __name__ == '__main__' else __file__


LAUNCH_COMPLETE = 'launch-complete'
BUILD_COMPLETE = 'build-complete'
FOLDER_NAME_LENGTH = 8
ALLOWED_FOLDER_CHARS = string.lowercase + string.digits


def log_exceptions(f):
    @wraps(f)
    def deco(*args, **kw):
        try:
            return f(*args, **kw)
        except:
            logging.exception()
            raise
    return deco

class Task:
    def __init__(self, email, message):
        self.email = email
        self.message = message
        self.instance_launched = False
        self.installer_location = None
    def is_complete(self):
        return self.instance_launched and self.installer_location

@log_exceptions
def check_qs(notify_q, builder_q, build_args):
    sqs = boto.sqs.connect_to_region("{{ grains['aws_region'] }}")
    ctrl_req_q = sqs.get_queue("{{ grains['controller'] }}_request")
    ctrl_req_q.set_message_class(JSONMessage)
    ctrl_notify_q = sqs.get_queue("notify_{{ grains['controller'] }}")
    ctrl_notify_q.set_message_class(JSONMessage)
    pending = {}
    while True:
        try:
            msg = notify_q.get(False)
            msg_type, email = msg[:2]
            task = pending[email]
            if msg_type == LAUNCH_COMPLETE:
                task.instance_launched = True
            elif msg_type == BUILD_COMPLETE:
                task.installer_location = msg[2]
            else:
                assert False
            if task.is_complete():
                del pending[email]
                logging.info("Reporting installers for %s are ready at %s."
                             % (clip_email(email), task.installer_location))
                msg = JSONMessage()
                msg.set_body(
                        {'invsrvup-user': email,
                         'invsrvup-insloc': task.installer_location})
                ctrl_notify_q.write(msg)
                ctrl_req_q.delete_message(task.message)
        except Empty:
            pass
        msg = ctrl_req_q.read()
        if msg is None:
            continue
        d = msg.get_body()
        # DRY warning: InvitedServerLauncher at lantern-controller.
        email = d['launch-invsrv-as']
        refresh_token = d['launch-refrtok']
        bucket = d['launch-bucket']
        logging.info("Got spawn request for '%s'"
                     % clip_email(email))
        pending[email] = Task(email, msg)
        Process(target=launch_instance,
                args=(email, refresh_token, bucket, build_args,
                      notify_q, builder_q)).start()
        # Give other servers a chance to handle any remaining messages.
        time.sleep(5)

@log_exceptions
def launch_instance(email, refresh_token, bucket, build_args, notify_q,
                    builder_q):
    creds_dict = {'username': email,
                  'access_token': 'whatever',
                  'refresh_token': refresh_token}
    user_creds_fp, user_creds_filename = tempfile.mkstemp(
                                               suffix='.user_credentials.json')
    user_creds_file = os.fdopen(user_creds_fp, 'w')
    instance_name = "inv%x" % hash(email)
    #XXX pick a random port in the appropriate range.
    port = 12345
    try:
        json.dump(creds_dict, user_creds_file)
        user_creds_file.close()
        while get_ip(instance_name):
            instance_name = 'invx%x' % hash(os.urandom(8))
        logging.info("Spawning %s..." % instance_name)
        os.system("salt-cloud -p aws %s" % instance_name)
        host = get_ip(instance_name)
        builder_q.put((email, host, port, bucket))
        #XXX Now I would initialize the server.  Pillars?
        notify_q.put((LAUNCH_COMPLETE, email))
    finally:
        os.remove(user_creds_filename)

def get_ip(instance_name):
    reservation, = connect().get_all_instances(filters={'tag:Name': name})
    instance, = reservation.instances
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
    return boto.ec2.connect_to_region(
            {{ grains['aws_region'] }},
            aws_access_key_id={{ grains['aws_id'] }},
            aws_secret_access_key={{ grains['aws_key'] }})


@log_exceptions
def build_installers_proc(notify_q, builder_q):
    while True:
        notify_q.put(build_installers(*builder_q.get()))

def build_installers(email, host, port, bucket):
    logging.info("Building installers for %s (%s:%s) bucket %s..."
                 % (clip_email(email), host, port, bucket))
    error = os.system("FALLBACK_SERVER_HOST=%s FALLBACK_SERVER_PORT=%s %s/build-installers.bash"
                      % (host, port, here))
    assert not error
    installer_location = upload_installers(bucket)
    logging.info("Installers for %s uploaded to %s."
                 % (clip_email(email), installer_location))
    return BUILD_COMPLETE, email, installer_location

def upload_installers(bucket_name):
    logging.info("Uploading installers to %s..." % bucket_name)
    conn = boto.connect_s3()
    bucket = conn.get_bucket(bucket_name)
    folder = get_random_folder_name(bucket)
    # DRY warning: suffixes, name structure.
    for arch, suffix in [('windows-x86', '.exe'),
                         ('osx', '.dmg'),
                         ('linux-x86', '-32-bit.deb'),
                         ('linux-amd64', '-64-bit.deb')]:
        filename = "lantern-%s%s" % (VERSION, suffix)
        key = Key(bucket)
        key.name = "%s/%s" % (folder, filename)
        key.storage_class = 'REDUCED_REDUNDANCY'
        logging.info("Uploading to %s" % key.name)
        key.set_contents_from_filename(os.path.join(here, 'lantern', filename))
        key.set_acl('public-read')
    return "%s/%s" % (bucket_name, folder)

def get_random_folder_name(bucket):
    while True:
        attempt = ''.join(random.choice(ALLOWED_FOLDER_CHARS)
                          for _ in xrange(FOLDER_NAME_LENGTH))
        try:
            iter(bucket.list(prefix=attempt)).next()
        except StopIteration:
            return attempt

def clip_email(email):
    at_index = email.find('@')
    return '%s...%s' % (email[:1], email[at_index-2:at_index])


if __name__ == '__main__':
    secrets_dir = here
    lantern_aws_dir = os.path.join(here, 'lantern_aws')
    logging.basicConfig(level=logging.INFO,
                        filename=os.path.join(here, 'invsrvlauncher.log'),
                        format='%(levelname)-8s %(message)s')
    try:
        _, client_secrets_filename, keystore_path = sys.argv
    except IndexError:
        # DRY warning: see also cloudmaster.init and init_files.py in master
        # branch.  Also make sure positions in the above try block remain
        # valid.
        logging.error(("Usage: %s"
               + " <client-secrets> <keystore-path>")
               % sys.argv[0])
        sys.exit(1)
    notify_q = Queue()
    builder_q = Queue()
    Process(target=build_installers_proc, args=(notify_q, builder_q)).start()
    check_qs(notify_q,
             builder_q,
             (lantern_id_rsa_filename, client_secrets_filename, keystore_path))
