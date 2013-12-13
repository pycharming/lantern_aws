#!/usr/bin/env bash

LOG=$(dirname $0)/install-lantern.log

set -e

[ ! -e lantern-repo ] || rm -rf lantern-repo
git clone --depth 1 git://github.com/getlantern/lantern.git \
                                lantern-repo > $LOG 2>&1
cd lantern-repo
git checkout {{ pillar['refspec'] }} >> $LOG 2>&1
git submodule update --init >> $LOG 2>&1
./install.bash >> $LOG 2>&1
echo
echo 'changed=yes'
