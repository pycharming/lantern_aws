#!/usr/bin/env bash

LOG=$(dirname $0)/install-lantern.log

set -e

[ ! -e lantern-repo ] || rm -rf lantern-repo > $LOG 2>&1
git clone --depth 1 --recursive --branch {{ pillar.get('branch', 'fallback') }} git://github.com/getlantern/lantern-java.git lantern-repo > $LOG 2>&1
cd lantern-repo
# Symlink pt to the right version of pt in install to get PluggableTransports support
ln -s install/linux_x86_64/pt pt
./install.bash >> $LOG 2>&1

echo
echo 'changed=yes'
