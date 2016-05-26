#!/bin/bash

# Based on https://raw.githubusercontent.com/lumerit/s3-shell-backups/master/s3-redis-backup.sh

function die() {
  echo $*
  exit 1
}

#### BEGIN CONFIGURATION ####

# set dates for backup rotation
NOWDATE=`date +%Y-%m-%d_%H:%M:%S`

# set backup directory variables
SRCDIR='/tmp/s3backups'
BUCKET='lantern_redis_backups'
DESTDIR='{{ pillar["environment"] }}'

#### END CONFIGURATION ####

BACKUP_FILE=${SRCDIR}/${NOWDATE}_redis_dump.rdb
echo $BACKUP_FILE

# make the temp directory if it doesn't exist
mkdir -p $SRCDIR || die "Could not create temp directory"

# make a compressed copy of the redis dump
cp /var/lib/redis/dump.rdb $BACKUP_FILE || die "Could not copy dump.rdb"
gzip $BACKUP_FILE || die "Could not gzip dump.rdb"

# send the file off to s3
/usr/bin/s3cmd put ${BACKUP_FILE}.gz s3://${BUCKET}/${DESTDIR}/ || die "Could not upload to S3"

# remove all files in our source directory
rm -f $SRCDIR/* || die "Could not delete temp directory"
