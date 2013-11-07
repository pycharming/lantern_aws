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
    r"lantern-net-installer_([a-z]+)_(.*)\.[a-z]+")
landing_template = file("/home/lantern/installer_landing.html").read()
# Keyed by platform as it appears in the wrapper filename.
content_types = {'windows': 'application/octet-stream',
                 'macos': 'application/x-apple-diskimage',
                 # By default, S3 will give .sh files a text/x-sh MIME type,
                 # which will cause them to be displayed in the browser, not
                 # downloaded.
                 'unix': 'application/x-sh'}

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
    newest_version = version
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
        # We use the original name for the landing page, so we have to rename
        # the wrappers somehow.  Since the wrappers are supposed to get the
        # latest installer, their version number is misleading (and we've had
        # comments against such low version numbers at this stage).  So let's
        # take that out.
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
        # We give it the URL that we used to give to the wrappers, to keep old
        # invite email links working, and to avoid having to change anything
        # in the controller and deal with whatever transition issues ensue.
        landing_key.name = "%s/%s" % (folder, filename)
        landing_key.storage_class = 'REDUCED_REDUNDANCY'
        logging.info("Uploading landing to %s" % landing_key.name)
        landing_key.set_metadata('Content-Type', 'text/html')
        landing_key.set_metadata('Content-Disposition', 'inline')
        landing_key.set_contents_from_string(
                landing_template.format(wrapper_name=s3_wrapper_filename,
                                        platform=platform),
                replace=True)
        landing_key.set_acl('public-read')

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
