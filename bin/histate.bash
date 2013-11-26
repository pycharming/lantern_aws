#!/usr/bin/env bash

$(dirname $0)/ssh_cloudmaster.py 'sudo salt -b 5 "fp-*" state.highstate' | tee hslog ; grep False hslog
