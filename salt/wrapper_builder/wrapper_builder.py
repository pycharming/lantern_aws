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
CONFIGURL_PATH = '/home/lantern/wrapper-repo/install/wrapper/.lantern-configurl.txt'


def build_wrappers(folder):
    # DRY: controller, cloudmaster.
    file(CONFIGURL_PATH, 'w').write(folder)
    ret = os.system("/home/lantern/build-wrappers.bash")
    return ret == 0

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
        # Generate landing page (just substitute .html for file extension.)
        landing_key = Key(bucket)
        extensionless = s3_wrapper_filename[:s3_wrapper_filename.rfind('.')]
        landing_key.name = "%s/%s.html" % (folder, extensionless)
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

def run():
    sqs = boto.sqs.connect_to_region(AWS_REGION, **aws_creds)
    # DRY: SQSUtil.WRAPPER_BUILD_REQUEST_Q_NAME in controller.
    ctrl_req_q = sqs.get_queue("%s_wrapper_build_request" % CONTROLLER)
    ctrl_req_q.set_message_class(JSONMessage)
    while True:
        logging.info("Checking queue...")
        # Wait time is not terribly important, since we're checking all the
        # time anyway.  This is just to prevent proliferation of "Nothing in
        # request queue." log messages.  So we set it to as much as AWS will
        # allow, which happens to be 20 seconds.
        msg = ctrl_req_q.read(wait_time_seconds=20)
        if msg is None:
            logging.info("Nothing in request queue.")
            continue
        d = msg.get_body()
        # DRY: S3Config.enqueueWrapperUploadRequest in controller.
        folder = d['upload-wrappers-to']
        id_ = d['upload-wrappers-id']
        while not build_wrappers(folder):
            logging.error("Failed to build wrappers!")
            # Let's hope this is a temporary condition.
            time.sleep(5)
        upload_wrappers(folder)
        report_wrappers_uploaded(sqs, id_)
        ctrl_req_q.delete_message(msg)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename="/home/lantern/wrapper_builder.log",
                        format='%(asctime)s %(levelname)-8s %(message)s')
    try:
        run()
    except:
        logging.exception("Uncaught top-level exception")
