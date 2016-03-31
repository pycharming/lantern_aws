#!/bin/bash

set -e

DIR=$(mktemp -d)

cd $DIR
git clone --branch=v1.0.0 --depth=1 git://github.com/firehol/netdata.git
cd netdata
./netdata-installer.sh --dont-start-it --dont-wait --zlib-is-really-here --install /opt
cd /tmp
rm -rf $DIR
touch /etc/netdata-installed
