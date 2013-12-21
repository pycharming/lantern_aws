#!/usr/bin/env bash

$(dirname $0)/ssh_cloudmaster.py 'sudo tail -f /home/lantern/cloudmaster.log'
