#!/usr/bin/env python

import os

import util


report_threshold = 0.8
split_threshold = 0.7


_, _, la15m = os.getloadavg()

print "starting..."

if la15m > report_threshold:
    print "report threshold surpassed; notifying..."
    util.send_alarm('Chained fallback high load',
                    "load average %s" % la15m)

if la15m > split_threshold:
    util.split_server("reached load average %s" % la15m)

print "... done."
