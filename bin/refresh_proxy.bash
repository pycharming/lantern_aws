#!/bin/bash

# This script deploys the latest configuration to a list of proxies and then
# reboots them to make sure everything is good.
DC=$1 bin/ssh_cloudmaster.py "sudo salt -b 25 -L \"$2\" state.highstate ; sudo salt -b 25 -L \"$2\" cmd.run \"shutdown -c ; reboot -n\""