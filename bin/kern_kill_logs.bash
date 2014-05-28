#!/usr/bin/env bash

$(dirname $0)/ssh_cloudmaster.py "sudo salt $1 cmd.run \"zgrep kill /var/log/kern.log*\""
