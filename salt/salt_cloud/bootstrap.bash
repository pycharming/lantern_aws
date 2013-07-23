#!/usr/bin/env bash

# Configure the machine where this script is run as a Salt
# (http://saltstack.org) minion.

HOSTNAME={{ vm['name'] }}

export DEBIAN_FRONTEND=noninteractive

# Feel free to comment this out if it causes any problems.  I was getting
# massive warning spam from perl because of a missing locale.
locale-gen en_US en_US.UTF-8 gl_ES.UTF-8
dpkg-reconfigure locales

# We configure the hostname before we generate the salt keys so we get the
# correct configuration to begin with and so we don't have to update salt keys
# later.
echo $HOSTNAME > /etc/hostname
hostname -F /etc/hostname

sed -i "s/^127.0.0.1.*$/127.0.0.1 $HOSTNAME localhost/" /etc/hosts

apt-get update -y
#apt-get upgrade -y
apt-get install python python-support python-pkg-resources python-crypto python-jinja2 python-m2crypto python-yaml python-zmq dctrl-tools msgpack-python python-markupsafe python-pip debconf-utils -y -o DPkg::Options::=--force-confold
apt-get autoremove -y
pip install --upgrade pip
hash -r

pip install salt==0.15.3

mkdir -p /etc/salt/pki/minion
echo '{{ vm['priv_key'] }}' > /etc/salt/pki/minion/minion.pem
echo '{{ vm['pub_key'] }}' > /etc/salt/pki/minion/minion.pub
echo "{{ minion }}" > /etc/salt/minion

salt-call state.highstate

echo "Salt bootstrap done."
