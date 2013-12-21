#!/usr/bin/env bash

$(dirname $0)/ssh_cloudmaster.py 'sudo salt-call state.highstate' | tee hslog
