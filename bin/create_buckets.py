#!/usr/bin/env python

import json
import os
import sys
import random
import string
import time

import boto
from boto.exception import S3CreateError

from bin_dir import bin_dir
sys.path.append(os.path.join(bin_dir(), '..', 'salt', 'xmpp'))
import xmpp_util

# (http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html)
#
# "Bucket name must be a series of one or more labels separated by a period
# (.), where each label:
#  -  Must start with a lowercase letter or a number
#  -  Must end with a lowercase letter or a number
#  -  Can contain lowercase letters, numbers and dashes"
#
# To make random bucket name generation slightly simpler, we don't use dashes.
#
# We avoid periods because (in the same page):
#
# "Bucket names must not be formatted as an IP address (e.g., 192.168.5.4)"
#
# ...and, more importantly:
#
# (http://docs.aws.amazon.com/AmazonS3/latest/dev/VirtualHosting.html)
#
# "When using virtual hosted-style buckets with SSL, the SSL wild card
# certificate only matches buckets that do not contain periods."
valid_bucket_name_characters = string.lowercase + string.digits

# A template to make a bucket only accessible through HTTPS.  Parameterized by
# bucket id.
policy_template = \
"""{"Statement": [{"Action": "s3:*",
                   "Effect":"Deny",
                   "Principal": "*",
                   "Resource": "arn:aws:s3:::%s/*",
                   "Condition": {"Bool": {"aws:SecureTransport": false}}}]}"""


def main(num_buckets, access_token):
    conn = boto.connect_s3()
    # boto.create_bucket(name) won't warn me if I already have a bucket called
    # `name`.  I check against this, lest I create less than `num_buckets`.
    taken_names = {b.name for b in conn.get_all_buckets()}
    bucket_names = []
    for _ in xrange(num_buckets):
        bname = create_bucket(conn, taken_names)
        taken_names.add(bname)
        bucket_names.append(bname)
    tell_lantern_controller(access_token, bucket_names)

def create_bucket(conn, taken_names):
    while True:
        name = random_bucket_name()
        if try_and_create_bucket(name, conn, taken_names):
            return name

def try_and_create_bucket(name, conn, taken_names):
    if name in taken_names:
        return False
    try:
        bucket = conn.create_bucket(name)
        bucket.set_policy(policy_template % name)
        return True
    except S3CreateError as e:
        if e.error_code == 'BucketAlreadyExists':
            return False
        else:
            raise

def random_bucket_name():
    length = urandint(8, 64)
    return ''.join(random_char() for _ in xrange(length))

def random_char():
    return valid_bucket_name_characters[
            urandint(0, len(valid_bucket_name_characters)-1)]

def urandint(min_, max_):
    random.seed(os.urandom(8))  # for good measure! :)
    return random.randint(min_, max_)

def tell_lantern_controller(access_token, bucket_names):
    bot = XmppBot(access_token, bucket_names)
    while not bot.connect():
        logging.warn("Trouble connecting to XMPP.  Retrying in one minute...")
        time.sleep(60)
    bot.process(block=True)

class XmppBot(xmpp_util.OAuth2Bot):
    def __init__(self, token, buckets):
        xmpp_util.OAuth2Bot.__init__(self, 'invsrvlauncher@gmail.com', token)
        self.body = json.dumps({'register-buckets': buckets})
    def session_start(self, event):
        xmpp_util.OAuth2Bot.session_start(self, event)
        self.send_message(xmpp_util.lanternctrl_jid, self.body, mtype='chat')
        self.disconnect(wait=True)

if __name__ == '__main__':
    try:
        num_buckets = int(sys.argv[1])
        client_secrets_filename = sys.argv[2]
        refresh_token_filename = sys.argv[3]
    except (IndexError, ValueError):
        print "Usage: %s <num_buckets> <client_secrets_file> <refresh_token_file>" % sys.argv[0]
        sys.exit(1)
    client_id, client_secret = xmpp_util.read_client_secrets(
            client_secrets_filename)
    refresh_token = file(refresh_token_filename).read()
    access_token = xmpp_util.get_access_token(client_id,
                                              client_secret,
                                              refresh_token)
    main(num_buckets, access_token)
