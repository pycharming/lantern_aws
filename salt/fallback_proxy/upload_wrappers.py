#!/usr/bin/env python

import re
import os

import boto


def upload_installers():
    conn = boto.connect_s3(**aws_creds)
    folder = get_random_folder_name()
    repo = os.path.join(here, 'repo')
    for suffix in ['.exe', '.dmg', '-32-bit.deb', '-64-bit.deb']:
        filename, = (s for s in os.listdir(repo)
                     if s.endswith(suffix))
        version, = re.match('lantern-(.*)%s' % suffix).groups()
        key = Key(BUCKET)
        key.name = "%s/%s" % (folder, filename)
        key.storage_class = 'REDUCED_REDUNDANCY'
        logging.info("Uploading to %s" % key.name)
        path = os.path.join(repo, filename)
        key.set_contents_from_filename(path)
        key.set_acl('public-read')
        os.unlink(path)
    return "%s/%s" % (folder, version)

def get_random_folder_name():
    bucket = boto.connect_s3(**aws_creds).get_bucket(BUCKET)
    while True:
        attempt = ''.join(random.choice(ALLOWED_FOLDER_CHARS)
                          for _ in xrange(FOLDER_NAME_LENGTH))
        try:
            iter(bucket.list(prefix=attempt)).next()
        except StopIteration:
            return attempt

