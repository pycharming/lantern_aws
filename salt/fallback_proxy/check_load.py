#!/usr/bin/env python

from datetime import datetime
import os
import sys

import util

if util.instance_id.startswith('fp-nl-201503'):
    # These are chronically overloaded from traffic by old clients. We can't do
    # much about them until we stop supporting those versions, so let's
    # suppress the noise.
    sys.exit(0)

retire_threshold = 3.0
report_threshold = 1.3
split_threshold = 0.9
# We don't want to retire overloaded servers while the refill queue is too
# empty, because that will strain the remaining servers, which might cause a
# cascade of fallbacks retiring themselves faster than we can launch them.
#
# We do this here and not in util.py, because that module is used by the
# traffic checks too, and this reasoning doesn't apply to that case: if many
# servers start running over quota, in the worst case we'd rather have some
# temporary downtime for some users than practically unbounded traffic costs.
min_q_size = 15


_, _, la15m = os.getloadavg()

print "Starting with load average %s..." % la15m

# We don't want to retire servers in the surge that made us split them, because
# we want to give splitting a chance to ease load on the server. So we check
# whether at least one day has elapsed since we split the server before we
# retire it because of load.
#
# We do this here, and not in util.py, because that module is used by the
# traffic checks too, and this reasoning doesn't apply to that case: once a
# server has consumed too much traffic there's no point in waiting before
# retiring it.
if la15m > report_threshold:
    print "report threshold surpassed; notifying..."
    util.send_alarm('Chained fallback high load',
                    "load average %s" % la15m)

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
          and la15m > retire_threshold
          and util.redis_shell.llen(util.dc + ":srvq") >= min_q_size)

if retire:
    print "I'll try retiring myself"
else:
    print "Not retiring myself"

if la15m > split_threshold:
    print "Splitting..."
    util.split_server("reached load average %s" % la15m,
                      retire)
else:
    print "Not splitting."

print "... done."
