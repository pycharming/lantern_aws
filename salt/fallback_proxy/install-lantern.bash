#!/usr/bin/env bash

BUCKET={{ pillar['installer_bucket'] }}
FILENAME={{ pillar['installer_filename'] }}

set -e

wget -cq https://s3.amazonaws.com/${BUCKET}/${FILENAME}
dpkg -i $FILENAME
rm $FILENAME
# Patch java args to claim 350MB.
sed -i 's,"-XX:+HeapDumpOnOutOfMemoryError","-Xmx350m" "-XX:+HeapDumpOnOutOfMemoryError",' /opt/lantern/lantern
echo
echo 'changed=yes'
