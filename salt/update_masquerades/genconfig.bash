#!/usr/bin/env bash

function die() {
  echo $*
  exit 1
}

./genconfig -blacklist="blacklist.txt" -masquerades="masquerades.txt" -proxiedsites="proxiedsites" -fallbacks="fallbacks.yaml" || die "Could not generate config?"

./cfg2redis.py cloud.yaml
