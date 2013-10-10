#!/usr/bin/env python

# Run this in the folder where the wrappers were built.

import logging
import os
import random
import re
import string

import boto
from boto.s3.key import Key

FOLDER_NAME_LENGTH = 8
ALLOWED_FOLDER_CHARS = string.lowercase + string.digits

# DRY warning: report_completion.py relies on this file name.
WRAPPER_LOCATION_PATH = "/home/lantern/wrapper_location"
BUCKET = "lantern-installers"
# DRY warning: ../cloudmaster/cloudmaster.py
AWS_ID = "{{ pillar['aws_id'] }}"
AWS_KEY = "{{ pillar['aws_key'] }}"
aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}
filename_re = re.compile(
    r"lantern-net-installer_[a-z]+_(.*)\.[a-z]+")


def upload_wrappers():
    conn = boto.connect_s3(**aws_creds)
    try:
        # If we have already uploaded wrappers from this instance, use the same
        # folder as before, so the links in old invite e-mails will point to the
        # new wrappers.
        loc = file(WRAPPER_LOCATION_PATH).read()
        path, version = loc.split(",")
        bucket_name, folder = path.split("/")
        bucket = conn.get_bucket(bucket_name)
    except IOError:
        bucket = conn.get_bucket(BUCKET)
        folder = get_random_folder_name(bucket)
        version = None
    for filename in os.listdir("."):
        m = filename_re.match(filename)
        if m is None:
            continue
        if version is None:
            version, = m.groups()
        else:
            v, = m.groups()
            if v != version:
                log.error("Several versions here?")
            # For robustness, we pick the newest, so the worst that will
            # happen is hopefully that we upload old wrappers in addition to
            # the newest ones, but we still point the controller to the right
            # ones.
            newest_version = max(v, version)
        key = Key(bucket)
        key.name = "%s/%s" % (folder, filename)
        key.storage_class = 'REDUCED_REDUNDANCY'
        # By default, .sh files will be given a text/x-sh MIME type, which
        # will cause them to be displayed in the browser, not downloaded.
        if filename.endswith('.sh'):
            key.set_metadata('Content-Type', 'application/x-sh')
        logging.info("Uploading to %s" % key.name)
        key.set_contents_from_filename(filename, replace=True)
        key.set_acl('public-read')
        # Delete successfully uploaded wrappers.
        os.unlink(filename)
    # DRY warning: lantern-controller needs to understand this format.
    file(WRAPPER_LOCATION_PATH, 'w').write(
            "%s/%s,%s" % (BUCKET, folder, newest_version))
    # DRY warning: the salt scripts use this file name as a state flag.
    file('/home/lantern/uploaded_wrappers', 'w').write('OK')

def get_random_folder_name(bucket):
    while True:
        attempt = ''.join(random.choice(ALLOWED_FOLDER_CHARS)
                          for _ in xrange(FOLDER_NAME_LENGTH))
        try:
            iter(bucket.list(prefix=attempt)).next()
        except StopIteration:
            return attempt


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename="/home/lantern/upload_wrappers.log",
                        format='%(levelname)-8s %(message)s')
    upload_wrappers()
