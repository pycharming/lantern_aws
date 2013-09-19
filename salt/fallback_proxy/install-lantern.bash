#!/usr/bin/env bash

wget -cq https://s3.amazonaws.com/lantern/latest-64.deb
dpkg -i latest-64.deb
rm latest-64.deb
echo
echo 'changed=yes'
