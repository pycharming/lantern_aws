#!/usr/bin/env bash

function fatal() {
  echo $* 1>&2
  exit 1
}

# We are already checking this in the .sls file, but it can't hurt to make
# sure.
[ $(swapon -s | wc -l) -le 1 ] || fatal "Swap already set up?"

SFPATH=/mnt/swapfile

set -e

dd if=/dev/zero of=$SFPATH bs=1024 count=4194304
chown root:root $SFPATH
chmod 0600 $SFPATH

mkswap $SFPATH
swapon $SFPATH

echo "$SFPATH       none    swap    sw      0       0" >> /etc/fstab

echo "Swap file initialized."
