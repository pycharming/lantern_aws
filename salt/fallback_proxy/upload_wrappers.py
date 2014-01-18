#!/usr/bin/env python

from base64 import b64decode
from cPickle import loads
import logging
import os
import random
import re
import string
import sys

import boto
from boto.s3.key import Key
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage
from lockfile import LockFile


UPLOAD_CWD = '/home/lantern/wrapper-repo/install'
BUCKET = "lantern-config"
CONTROLLER = "{{ grains['controller'] }}"
# DRY warning: ../cloudmaster/cloudmaster.py
AWS_REGION = "{{ grains['aws_region'] }}"
AWS_ID = "{{ pillar['aws_id'] }}"
AWS_KEY = "{{ pillar['aws_key'] }}"
aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}
filename_re = re.compile(
    r"lantern-net-installer_([a-z]+)_(.*)\.[a-z]+")
landing_template = file("/home/lantern/installer_landing.html").read()
# Keyed by platform as it appears in the wrapper filename.
content_types = {'windows': 'application/octet-stream',
                 'macos': 'application/x-apple-diskimage',
                 # By default, S3 will give .sh files a text/x-sh MIME type,
                 # which will cause them to be displayed in the browser, not
                 # downloaded.
                 'unix': 'application/x-sh'}
# DRY
CONFIGURL_PATH = '/home/lantern/wrapper-repo/install/wrapper/configurl.txt'
LEGACY_PATH = '/home/lantern/wrapper-repo/install/wrapper/fallback.json'

def build_and_upload_wrappers(sqs_msg):
    sqs_msg = loads(b64decode(sqs_msg))
    folder = sqs_msg.get_body()['upload-wrappers-to']
    id_ = sqs_msg.get_body()['upload-wrappers-id']
    build_wrappers(folder)
    upload_wrappers(folder)
    sqs = boto.sqs.connect_to_region(AWS_REGION, **aws_creds)
    report_wrappers_uploaded(sqs, id_)
    sqs.get_queue("%s_request" % CONTROLLER).delete_message(sqs_msg)

def build_wrappers(folder):
    # DRY: controller, cloudmaster.
    file(CONFIGURL_PATH, 'w').write(folder)
    file(LEGACY_PATH, 'w').write('{"no": "more"}')
    ret = os.system("/home/lantern/build-wrappers.bash")
    assert ret == 0

def upload_wrappers(folder):
    os.chdir(UPLOAD_CWD)
    conn = boto.connect_s3(**aws_creds)
    bucket = conn.get_bucket(BUCKET)
    newest_version = version = None
    for filename in os.listdir("."):
        m = filename_re.match(filename)
        if m is None:
            continue
        if version is None:
            platform, version = m.groups()
            newest_version = version
        else:
            platform, version = m.groups()
            if version != newest_version:
                logging.error("Several versions here?")
            # For robustness, we pick the newest, so the worst that will
            # happen is hopefully that we upload old wrappers in addition to
            # the newest ones, but we still point the controller to the right
            # ones.
            newest_version = max(newest_version, version)
        wrapper_key = Key(bucket)
        # Strip version info from wrapper filenames, since we're not really
        # maintaining it.
        s3_wrapper_filename = filename.replace("_" + version, '')
        wrapper_key.name = "%s/%s" % (folder, s3_wrapper_filename)
        wrapper_key.storage_class = 'REDUCED_REDUNDANCY'
        wrapper_key.set_metadata('Content-Type', content_types[platform])
        wrapper_key.set_metadata('Content-Disposition', 'attachment')
        logging.info("Uploading wrapper to %s" % wrapper_key.name)
        wrapper_key.set_contents_from_filename(filename, replace=True)
        wrapper_key.set_acl('public-read')
        # Delete successfully uploaded wrappers.
        os.unlink(filename)
        # Generate landing page.
        landing_key = Key(bucket)
        landing_key.name = "%s/%s.html" % (folder, s3_wrapper_filename)
        landing_key.storage_class = 'REDUCED_REDUNDANCY'
        logging.info("Uploading landing to %s" % landing_key.name)
        landing_key.set_metadata('Content-Type', 'text/html')
        landing_key.set_metadata('Content-Disposition', 'inline')
        landing_key.set_contents_from_string(
                landing_template.format(wrapper_name=s3_wrapper_filename,
                                        platform=platform),
                replace=True)
        landing_key.set_acl('public-read')

def report_wrappers_uploaded(sqs, id_):
    msg = JSONMessage()
    msg.set_body({'wrappers-uploaded-for': id_})
    sqs.get_queue("notify_%s" % CONTROLLER).write(msg)

def serialize(lock_filename, thunk):
    with LockFile(lock_filename):
        try:
            thunk()
        except Exception as e:
            logging.exception(e)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename="/home/lantern/upload_wrappers.log",
                        format='%(levelname)-8s %(message)s')
    serialize(sys.argv[0], lambda: build_and_upload_wrappers(sys.argv[1]))
