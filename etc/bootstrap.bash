#!/usr/bin/env bash

# Configure the machine where this script is run as a Salt
# (http://saltstack.org) master and minion.  By the time you run this, the
# server states should have been uploaded to /srv/salt.

HOSTNAME=cloudmaster

export DEBIAN_FRONTEND=noninteractive

LOG=/tmp/salt-bootstrap.log

# Feel free to comment this out if it causes any problems.  I was getting
# massive warning spam from perl because of a missing locale.
locale-gen en_US en_US.UTF-8 gl_ES.UTF-8
dpkg-reconfigure locales

# We configure the hostname before we generate the salt keys so we get the
# correct configuration to begin with and so we don't have to update salt keys
# later.
echo $HOSTNAME > /etc/hostname
hostname -F /etc/hostname

# 'salt' alias is so the minion will find the local master.
sed -i "s/^127.0.0.1.*$/127.0.0.1 $HOSTNAME localhost salt/" /etc/hosts

apt-get install python-software-properties -y > >(tee -a $LOG) 2>&1
add-apt-repository ppa:saltstack/salt -y > >(tee -a $LOG) 2>&1
apt-get update -y > >(tee -a $LOG) 2>&1
apt-get upgrade -y > >(tee -a $LOG) 2>&1
apt-get autoremove -y > >(tee -a $LOG) 2>&1
apt-get install salt-master -y > >(tee -a $LOG) 2>&1

# For some reason salt-minion's installer will ask us about overwritting
# /etc/salt/minion, despite our efforts to make it clear we don't want to
# interact with it.
mv /etc/salt/minion /etc/salt/minion.bak
apt-get install salt-minion -y > >(tee -a $LOG) 2>&1
mv /etc/salt/minion.bak /etc/salt/minion
service salt-minion restart

apt-get install python-libcloud -y > >(tee -a $LOG) 2>&1
apt-get install python-pip -y > >(tee -a $LOG) 2>&1
pip install --upgrade pip > >(tee -a $LOG) 2>&1
pip install boto > >(tee -a $LOG) 2>&1
pip install salt-cloud > >(tee -a $LOG) 2>&1

while [ ! -e /etc/salt/pki/master/minions_pre/$HOSTNAME ]
do
    echo "Key not preaccepted yet; waiting..." > >(tee -a $LOG) 2>&1
    sleep 1
done

# Make extra sure we are accepting the local key.
rm /etc/salt/pki/master/minions_pre/$HOSTNAME
cp /etc/salt/pki/minion/minion.pub /etc/salt/pki/master/minions/$HOSTNAME

salt-call state.highstate > >(tee -a $LOG) 2>&1

echo "Salt bootstrap done." > >(tee -a $LOG) 2>&1
