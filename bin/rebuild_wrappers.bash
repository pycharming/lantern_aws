#!/usr/bin/env bash

$(dirname $0)/update.py && $(dirname $0)/ssh_cloudmaster.py 'sudo salt "fp-*" cmd.run "rm /home/lantern/wrappers_built /home/lantern/uploaded_wrappers /home/lantern/reported_completion"' && $(dirname $0)/ssh_cloudmaster.py 'sudo salt "fp-*" state.highstate' | tee hslog ; echo "If there is any printout below, you may want to inspect the hslog file for errors:" ; grep False hslog
