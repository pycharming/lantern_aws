#!/usr/bin/env bash

# Configure the machine where this script is run as a Salt
# (http://saltstack.org) master and minion.  By the time you run this, the
# server states should have been uploaded to /srv/salt.

export DEBIAN_FRONTEND=noninteractive

LOG=/tmp/salt-bootstrap.log

# Feel free to comment this out if it causes any problems.  I was getting
# massive warning spam from perl because of a missing locale.
locale-gen en_US en_US.UTF-8 gl_ES.UTF-8
dpkg-reconfigure locales

wget -O - "https://bootstrap.saltstack.com" | sh -s -- -M git $SALT_VERSION > >(tee -a $LOG) 2>&1

while [ ! -e /etc/salt/pki/master/minions_pre/$(hostname) ]
do
    echo "Key not preaccepted yet; waiting..." > >(tee -a $LOG) 2>&1
    sleep 1
done

# Make extra sure we are accepting the local key.
rm /etc/salt/pki/master/minions_pre/$(hostname)
cp /etc/salt/pki/minion/minion.pub /etc/salt/pki/master/minions/$(hostname)

salt-call state.highstate > >(tee -a $LOG) 2>&1

echo "Salt bootstrap done." > >(tee -a $LOG) 2>&1
