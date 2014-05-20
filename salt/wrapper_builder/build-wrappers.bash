#!/usr/bin/env bash

set -e
cd /home/lantern/wrapper-repo
source ../secure/env-vars.txt && ./buildInstallerWrappers.bash >> /home/lantern/build-wrappers.log 2>&1

