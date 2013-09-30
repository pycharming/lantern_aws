#!/usr/bin/env bash

BUCKET={{ pillar['installer_bucket'] }}
FILENAME={{ pillar['installer_filename'] }}

wget -cq https://s3.amazonaws.com/${BUCKET}/${FILENAME}
dpkg -i $FILENAME
rm $FILENAME
echo
echo 'changed=yes'
