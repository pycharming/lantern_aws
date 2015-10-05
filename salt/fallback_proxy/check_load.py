#!/usr/bin/env python

import os
import sys

import util

if util.instance_id.startswith('fp-nl-201503'):
    # These are chronically overloaded from traffic by old clients. We can't do
    # much about them until we stop supporting those versions, so let's
    # suppress the noise.
    sys.exit(0)

report_threshold = 1.3
split_threshold = 0.9


_, _, la15m = os.getloadavg()

print "starting..."

if la15m > report_threshold:
    print "report threshold surpassed; notifying..."
    util.send_alarm('Chained fallback high load',
                    "load average %s" % la15m)

if la15m > split_threshold:
    util.split_server("reached load average %s" % la15m)

print "... done."
