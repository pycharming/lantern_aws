#!/usr/bin/env python

# Run this in the folder where the wrappers were built.

import logging
import os
import random as random_
import re
import string

import boto
from boto.s3.key import Key

random = random_.SystemRandom()

# The URL of the newly uploaded config will be of the form
#
#     https://s3.amazonaws.com/lantern-config/<key>
#
# where 'lantern-config' is the S3 bucket name and `key` is the randomly
# generated part of the path name.
#
# http://docs.aws.amazon.com/AmazonS3/latest/dev/UsingMetadata.html
#
# "The name for a key is a sequence of Unicode characters whose UTF-8 encoding
# is at most 1024 bytes long."
KEY_LENGTH = 1024
# For simplicity, and because the key space is absurdly vast anyway, let's just
# use characters that don't need to be percent encoded in a URL path.
#
# http://tools.ietf.org/html/rfc3986#section-2.3
ALLOWED_KEY_CHARS = string.letters + string.digits + "-._~"

BUCKET = "lantern-config"
# DRY warning: init.sls
SRC_FILENAME = "/home/lantern/fallback.json"
# DRY warning: ../cloudmaster/cloudmaster.py
AWS_ID = "{{ pillar['aws_id'] }}"
AWS_KEY = "{{ pillar['aws_key'] }}"
aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}

def upload_config():
    conn = boto.connect_s3(**aws_creds)
    bucket = conn.get_bucket(BUCKET)
    wrapper_key = Key(bucket)
    wrapper_key.name = get_random_key(bucket)
    logging.info("Uploading wrapper to %s" % wrapper_key.name)
    wrapper_key.set_contents_from_filename(SRC_FILENAME, replace=True)
    wrapper_key.set_acl('public-read')
    file('{{ config_url }}', 'w').write(
            "https://s3-{{ grains['aws_region'] }}.amazonaws.com/%s/%s"
            % (BUCKET, wrapper_key.name))

def get_random_key(bucket):
    while True:
        attempt = ''.join(random.choice(ALLOWED_KEY_CHARS)
                          for _ in xrange(KEY_LENGTH))
        try:
            iter(bucket.list(prefix=attempt)).next()
        except StopIteration:
            return attempt
        logging.warn("Unbelievably improbable clash: %r" % attempt)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename="/home/lantern/upload_config.log",
                        format='%(levelname)-8s %(message)s')
    upload_config()
