#!/usr/bin/env bash

$(dirname $0)/ssh_cloudmaster.py 'sudo salt "fp-*" grains.get ipv4'
