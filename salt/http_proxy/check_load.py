#!/usr/bin/env python

from datetime import datetime
import os
import sys

import psutil
from uptime import uptime

import util


# Avoid false positives by system load caused by machine setup or startup.
if uptime() < 60 * 45:
    print "Ignoring load average; I have just launched/booted."
    sys.exit(0)

if psutil.virtual_memory().total < 800000000:
    # As of this writing only 768MB Vultr instances meet this condition.
    retire_threshold = 1.1
    report_threshold = 1.0
    split_threshold = 0.9
else:
    # 1GB boxes.
    retire_threshold = 0.55
    report_threshold = 0.5
    split_threshold = 0.45

# We don't want to retire overloaded servers while the refill queue is too
# empty, because that will strain the remaining servers, which might cause a
# cascade of fallbacks retiring themselves faster than we can launch them.
#
# We do this here and not in util.py, because that module is used by the
# traffic checks too, and this reasoning doesn't apply to that case: if many
# servers start running over quota, in the worst case we'd rather have some
# temporary downtime for some users than practically unbounded traffic costs.
min_q_size = 15


# Using the 15m load average, because we have observed that 5m yields some
# false positives when running Salt updates.
_, _, lavg = os.getloadavg()

print "Starting with load average %s..." % lavg

if lavg > report_threshold:
    print "report threshold surpassed; notifying..."
    util.send_alarm('Chained fallback high load',
                    "load average %s" % lavg)

# We don't want to retire servers in the surge that made us split them, because
# we want to give splitting a chance to ease load on the server. So we check
# whether at least one day has elapsed since we split the server before we
# retire it because of load.
#
# We do this here, and not in util.py, because that module is used by the
# traffic checks too, and this reasoning doesn't apply to that case: once a
# server has consumed too much traffic there's no point in waiting before
# retiring it.
try:
    s = file(util.split_flag_filename).read()
    t0 = datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f')
    split_long_ago = (datetime.utcnow() - t0).days > 1
except IOError:
    split_long_ago = False
except ValueError:
    # Some old manually split servers have flag files that are empty or have
    # contents that are not valid datetime isoformats.
    split_long_ago = True

retire = (split_long_ago
          and lavg > retire_threshold
          and util.redis_shell.llen(util.region + ":srvq") >= min_q_size)


if lavg > split_threshold:
    print "Splitting..."
    util.split_server("reached load average %s" % lavg)
else:
    print "Not splitting."

if retire:
    print "Retiring..."
    util.retire_server("reached load average %s" % lavg)
else:
    print "Not retiring."

print "... done."
