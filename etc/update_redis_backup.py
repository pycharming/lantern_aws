#!/usr/bin/env python

# This is meant to run in the cfgsrv-redis-backup droplet, as a cron job every
# minute or so, under user redis.
#
# AWS credentials need to be set up so that boto will pick them up. See:
#
# http://boto.cloudhackers.com/en/latest/s3_tut.html#creating-a-connection

from datetime import datetime
import os

import boto
from dateutil.parser import parse as parse_time


last_backup_time_filename = '/home/redis/last_backup_time'
tmp_rdb_filename = '/home/redis/dump.rdb'
live_rdb_filename = '/var/lib/redis/dump.rdb'


def parse_last_modified(k):
    return parse_time(k.last_modified)

def run():
    s3 = boto.connect_s3()
    bucket = s3.get_bucket('rediscloud')
    keys = bucket.list()
    k = max(keys, key=parse_last_modified)
    try:
        last_backup_time = parse_time(file(last_backup_time_filename).read())
	if parse_last_modified(k) <= last_backup_time:
            print "Current backup is already the most recent; exiting."
            return
    except IOError:
        print "First backup ever!"
    print "Got new backup! Downloading..."
    f = open(tmp_rdb_filename, 'w')
    k.get_contents_to_file(f)
    print "Stopping redis server..."
    error = os.system('service redis-server stop')
    if error:
        print "Error trying to stop redis-server:", error
        return
    print "Replacing dump file..."
    os.rename(tmp_rdb_filename, live_rdb_filename)
    print "Starting redis server..."
    error = os.system('service redis-server start')
    if error:
        print "Error trying to start redis-server:", error
        return
    print "Saving new backup time..."
    file(last_backup_time_filename, 'w').write(k.last_modified)
    print "Done."


if __name__ == '__main__':
    run()
