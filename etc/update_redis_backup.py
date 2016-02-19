#!/usr/bin/env python

# This is meant to run in the cfgsrv-redis-backup droplet, as a cron job every
# minute or so, under user redis.
#
# AWS credentials need to be set up so that boto will pick them up. See:
#
# http://boto.cloudhackers.com/en/latest/s3_tut.html#creating-a-connection

from datetime import datetime
import os
import sys

import boto
from dateutil.parser import parse as parse_time


last_backup_time_filename = '/home/redis/last_backup_time'
tmp_rdb_filename = '/home/redis/dump.rdb'
live_rdb_filename = '/var/lib/redis/dump.rdb'


def bytes2mb(bytes):
    return bytes / 1024. / 1024.

def cb(bytes, total):
    print "%.2f of %.2f MB (%.2f%%)" % (bytes2mb(bytes),
                                        bytes2mb(total),
                                        bytes * 100. / total)

def parse_last_modified(k):
    return parse_time(k.last_modified)

def try_cmd(description, cmd, on_error=sys.exit):
    print "%s..." % description.capitalize()
    error = os.system(cmd)
    if error:
        raise RuntimeError("Error %s: %s" % (description, error))

def run():
    s3 = boto.connect_s3()
    bucket = s3.get_bucket('rediscloud')
    keys = bucket.list()
    k = max(keys, key=parse_last_modified)
    try:
        last_backup_time = parse_time(file(last_backup_time_filename).read())
        if parse_last_modified(k) <= last_backup_time:
            print "Current backup is already the most recent one; exiting."
            return
    except IOError:
        print "First backup ever!"
    print "Got new backup! Downloading %s..." % k.name
    for suffix in ['', '.gz']:
        path = tmp_rdb_filename + suffix
        if os.path.exists(path):
            os.unlink(path)
    k.get_contents_to_filename(tmp_rdb_filename + ".gz", cb=cb)
    try_cmd('uncompressing backup', 'gunzip %s.gz' % tmp_rdb_filename)
    try_cmd('stopping redis server', 'service redis-server stop')
    print "Replacing dump file..."
    os.rename(tmp_rdb_filename, live_rdb_filename)
    try_cmd('starting redis server', 'service redis-server start')
    print "Saving new backup time..."
    file(last_backup_time_filename, 'w').write(k.last_modified)
    print "Done."


if __name__ == '__main__':
    run()
