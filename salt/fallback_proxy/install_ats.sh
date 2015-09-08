#! /usr/bin/env sh

PREFIX=/opt/ts
LOG=$(dirname $0)/install-ats.log

set -e

echo 'Installing ats 5.3.1 package...'
[ ! -e $PREFIX ] || rm -rf $PREFIX > $LOG 2>&1
mkdir -p $PREFIX
chown lantern:lantern $PREFIX
(curl -L https://s3.amazonaws.com/lantern-aws/apache-traffic-server-5.3.1-ubuntu-14-64bit.tar.gz | sudo -u lantern tar zxC $PREFIX) >> $LOG 2>&1
cp $PREFIX/bin/trafficserver /etc/init.d/ >> $LOG 2>&1
echo 'Done'
