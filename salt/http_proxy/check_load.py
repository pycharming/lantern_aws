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

cpus = psutil.cpu_count()
retire_threshold = 2.0 * cpus
report_threshold = 1.6 * cpus
close_threshold = 1.2 * cpus


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

# Allow us to override any of the above locally in some machines. For example,
# we may not want fallback proxies to retire themselves even if they're
# overloaded.
try:
    from check_load_overrides import *
except ImportError:
    pass

if lavg > report_threshold:
    print "report threshold surpassed; notifying..."
    util.send_alarm('Chained fallback high load',
                    "load average %s" % lavg)

# We don't want to retire servers in the surge that made us close them, because
# load usually eases after closing and we want to give it a chance to
# stabilize. So we check whether at least one day has elapsed since we closed
# the server before we retire it because of load.
#
# We do this here, and not in util.py, because that module is used by the
# traffic checks too, and this reasoning doesn't apply to that case: once a
# server has consumed too much traffic there's no point in waiting before
# retiring it.
try:
    s = file(util.close_flag_filename).read()
    t0 = datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f')
    closed_long_ago = (datetime.utcnow() - t0).days > 1
except IOError:
    closed_long_ago = False
except ValueError:
    # Some old manually closed servers have flag files that are empty or have
    # contents that are not valid datetime isoformats.
    closed_long_ago = True

retire = (closed_long_ago
          and lavg > retire_threshold
          and util.redis_shell.llen(util.region + ":srvq") >= min_q_size)


if lavg > close_threshold:
    print "Closing..."
    util.close_server("reached load average %s" % lavg)
else:
    print "Not closing."

if retire:
    print "Retiring..."
    util.retire_server("reached load average %s" % lavg)
else:
    print "Not retiring."

print "... done."
