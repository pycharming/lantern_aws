#!/bin/bash

# Declare these here so they are not leaked (e.g.) in the ps output.
export CFR_ID={{ pillar['cfr_id'] }}
export CFR_KEY={{ pillar['cfr_key'] }}

/usr/bin/cfrjanitor 2>&1 | logger -t cfrjanitor
