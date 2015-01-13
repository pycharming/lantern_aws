#!/usr/bin/env bash

function fatal() {
  echo $* 1>&2
  exit 1
}

# We are already checking this in the .sls file, but it can't hurt to make
# sure.
[ $(swapon -s | wc -l) -eq 1 ] || fatal "Swap already set up?"

SFPATH=/mnt/swapfile

set -e

fallocate -l 4096M $SFPATH
chown root:root $SFPATH
chmod 0600 $SFPATH

mkswap $SFPATH
swapon $SFPATH

echo "$SFPATH       none    swap    sw      0       0" >> /etc/fstab

echo "Swap file initialized."
