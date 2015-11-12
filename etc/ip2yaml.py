#!/usr/bin/env python

import re
import sys

try:
    import vps_util
except ImportError:
    print >> sys.stderr, "You need lantern_aws/lib in your PYTHONPATH to run this."
    sys.exit(1)


if len(sys.argv) != 2 or not re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
                                      sys.argv[1]):
    print >> sys.stderr, "Usage: %s <ip-address>" % sys.argv[0]
    sys.exit(1)

ip = sys.argv[1]

print >> sys.stderr, "Fetching configs..."
byip = vps_util.srv_cfg_by_ip()
print >> sys.stderr, "... done."
print >> sys.stderr, ""

if ip in byip:
    print byip[ip][0]
else:
    print >> sys.stderr, "IP not found!"
