#!/usr/bin/env bash

# Remove the old one.
$(dirname $0)/ssh_cloudmaster.py 'sudo salt "fp-*" cmd.run "rm -rf /home/lantern/lantern-repo"'

# Re-apply the salt state so Lantern is installed again.  We have configured
# salt to restart the lantern service when this happens.
$(dirname $0)/ssh_cloudmaster.py 'sudo salt "fp-*" state.highstate'
