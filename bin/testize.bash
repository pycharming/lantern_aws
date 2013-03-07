#!/usr/bin/env bash

# A quick-and-dirty script to coerce an invsrvlauncher to point to a
# given lanternctrl.  I copy it over to /home/invsrvlauncher and run it there.

LANTERNCTRLID=lanternctrltest

git config --global user.email "blah@blah.blah"
git config --global user.name blah

cd /home/invsrvlauncher
sed -i s/lanternctrl@/${LANTERNCTRLID}@/ xmpp_util.py
cd /home/invsrvlauncher/lantern_aws
git checkout lantern-peer
sed -i 's/\"--disable-ui/\"--controller-id lanternctrltest --disable-ui/' salt/lantern/init-script
git commit -am .
git checkout master
cd /home/invsrvlauncher
sudo /etc/init.d/invsrvlauncher restart
