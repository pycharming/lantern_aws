#!/usr/bin/env python

from datetime import datetime
from multiprocessing import cpu_count
import os
import sys

from uptime import uptime

from alert import alert
import util


# Avoid false positives by system load caused by machine setup or startup.
if uptime() < 60 * 45:
    print "Ignoring load average; I have just launched/booted."
    sys.exit(0)

cpus = cpu_count()
# We believe that a proxy hitting this load is well utilized and shouldn't take
# on more users.
close_threshold = 0.9 * cpus
# Once a proxy hits this load we want to be warned about it.
report_threshold = 1.1 * cpus
# A proxy that hits this load is probably overwhelmed and we want to take users
# off it.
offload_threshold = 1.3 * cpus

# We don't want to offload overloaded servers while the refill queue is too
# empty, because that will strain the remaining servers, which might cause a
# cascade of offloading faster than we can launch proxies to take the excess
# load.
#
# We do this here and not in util.py, because that module is used by the
# traffic checks too, and this reasoning doesn't apply to that case: if many
# servers start running over quota, in the worst case we'd rather have some
# temporary downtime for some users than practically unbounded traffic costs.
min_q_size = 10


# Using the 15m load average, because we have observed that 5m yields some
# false positives when running Salt updates.
_, _, lavg = os.getloadavg()

print "Starting with load average %s..." % lavg

# Allow us to override any of the above locally in some machines.
try:
    from check_load_overrides import *
except ImportError:
    pass

if lavg > report_threshold:
    print "report threshold surpassed; notifying..."
    alert(type='high-proxy-load',
          details={'load-avg': lavg},
          title='High load in proxy',
          text="Load average %s" % lavg)

# We don't want to offload servers in the surge that made us close them, because
# load usually eases after closing and we want to give the proxy a chance to
# stabilize. So we check whether at least one day has elapsed since we closed
# the server before we offload it.
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

offload = (closed_long_ago
           and lavg > offload_threshold
           and util.redis_shell.llen(util.region + ":srvq") >= min_q_size)


msg = "reached load average %s" % lavg

if lavg > close_threshold:
    print "Closing..."
    util.close_server(msg)
else:
    print "Not closing."

if offload:
    print "Offloading..."
    if not util.am_I_closed():
        # In the current logic this should never be true, because the close
        # threshold is lower than the offload one. Anyway, adding this for
        # robustness to change and to highlight the fact that trying to offload
        # an open proxy to the slice table is silly, since users will come back
        # to it.
        util.close_server(msg)
    util.offload_server(msg,
                        proportion=0.33,
                        replace=False)
else:
    print "Not offloading."

print "... done."
