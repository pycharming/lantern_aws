#!/usr/bin/env bash

function fatal() {
  echo $* 1>&2
  exit 1
}

# We are already checking this in the .sls file, but it can't hurt to make
# sure.
[ $(swapon -s | wc -l) -eq 1 ] || fatal "Swap already set up?"

set -e

fallocate -l 2048M /swapfile
chown root:root /swapfile
chmod 0600 /swapfile

mkswap /swapfile
swapon /swapfile

echo "/swapfile       none    swap    sw      0       0" >> /etc/fstab

echo "Swap file initialized."
