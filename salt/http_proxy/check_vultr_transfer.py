#!/usr/bin/env python
from __future__ import division

from datetime import datetime as dt
import os
import random
import time

from vultr.vultr import Vultr, VultrError

import util


instance_id = "{{ grains['id'] }}"
# For offline testing.
if instance_id.startswith("{"):
    instance_id = "fp-jp-20150531-001"
vultr_subid_filename = "vultr_id"

api_key = "{{ pillar['vultr_apikey'] }}"
# For offline testing.
if api_key.startswith("{"):
    api_key = os.getenv("VULTR_APIKEY")
vultr = Vultr(api_key)

# Servers reaching this threshold at any time of the month are closed and their
# current users are reassigned to other servers.
retire_threshold = 0.95

def vultr_dict():
    while True:
        try:
            try:
                subid = file(vultr_subid_filename).read()
            except IOError:
                for d in vultr.server_list(None).itervalues():
                    if d['label'] == instance_id:
                        file(vultr_subid_filename, 'w').write(d['SUBID'])
                        return d
            return vultr.server_list(subid)
        except VultrError:
            time.sleep(10 * random.random() * 20)

def usage_portion(vd):
    allowed = int(vd['allowed_bandwidth_gb'])
    current = vd['current_bandwidth_gb']
    return current / allowed

def time_portion():
    now = dt.utcnow()
    beginning_of_month = dt(year=now.year, month=now.month, day=1)
    if now.month == 12:
        beginning_of_next_month = dt(year=now.year+1, month=1, day=1)
    else:
        beginning_of_next_month = dt(year=now.year, month=now.month+1, day=1)
    whole_month = beginning_of_next_month - beginning_of_month
    elapsed = now - beginning_of_month
    return elapsed.total_seconds() / whole_month.total_seconds()

def run():
    print "Starting..."
    vd = vultr_dict()
    usage = usage_portion(vd)
    msg = ("used %sGB out of %sGB allowed traffic quota (%.2f%%)"
           % (vd['current_bandwidth_gb'],
              vd['allowed_bandwidth_gb'],
              usage * 100))
    if usage > retire_threshold:
        print "Retiring because I", msg
        closed = util.am_I_closed()
        util.close_server(msg)
        util.retire_server(msg, offload=closed)
    else:
        print "Usage portion: %s; not retiring." % usage
    print "Done."


if __name__ == '__main__':
    run()
