#!/usr/bin/env bash

source ../secure/env-vars.txt && ./buildInstallerWrappers.bash $(../getlanternversion.py) && touch ../wrappers_built

