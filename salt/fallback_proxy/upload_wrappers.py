#!/usr/bin/env python

import logging
import os
import random
import re
import string

import boto
from boto.s3.key import Key

FOLDER_NAME_LENGTH = 8
ALLOWED_FOLDER_CHARS = string.lowercase + string.digits

BUCKET = "lantern-installers"
# DRY warning: ../cloudmaster/cloudmaster.py
AWS_ID = "{{ grains['aws_id'] }}"
AWS_KEY = "{{ grains['aws_key'] }}"
aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}
filename_re = re.compile(
    r"lantern-net-installer_[a-z]+_(.*)\.[a-z]+")


def upload_wrappers():
    conn = boto.connect_s3(**aws_creds)
    bucket = conn.get_bucket(BUCKET)
    folder = get_random_folder_name(bucket)
    # Run this in the folder where the wrappers were built.
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
        logging.info("Uploading to %s" % key.name)
        key.set_contents_from_filename(filename)
        key.set_acl('public-read')
        # Delete successfully uploaded wrappers.
        os.unlink(filename)
    file('/home/lantern/uploaded_wrappers', 'w').write(
            # DRY warning: lantern-controller needs to understand this format.
            "%s/%s,%s" % (BUCKET, folder, newest_version))

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
