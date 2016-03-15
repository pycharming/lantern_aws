#!/usr/bin/env python

"""
Kill zombie highstate jobs in bad minions.
"""

import os

import vps_util


bad = file('bad').read().split(',')

pids = map(vps_util.highstate_pid, bad)

for name, pid in zip(bad, pids):
    if pid:
        os.system('salt %s cmd.run "kill -9 %s"' % (name, pid))
