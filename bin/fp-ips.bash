#!/usr/bin/env bash

if [ -z $1 ] ; then
    TARGET='fp-*'
else
    TARGET="$1"
fi

$(dirname $0)/ssh_cloudmaster.py "sudo salt \"$TARGET\" grains.get ipv4" | grep -v 127.0.0.1
