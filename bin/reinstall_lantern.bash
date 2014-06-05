#!/usr/bin/env bash

# Update from git, build, restart
$(dirname $0)/ssh_cloudmaster.py 'sudo salt "fp-*" cmd.run "export PATH=/usr/local/apache-maven-3.1.1/bin/:$PATH && cd /home/lantern/lantern-repo && git pull && git submodule update && ./install.bash && sudo service lantern stop; sudo service lantern start"'
