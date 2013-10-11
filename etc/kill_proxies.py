#!/usr/bin/env python

# Kill all fallback proxies in the given list and remove them from the
# cloudmaster's map.  The latter step is necessary so the cloudmaster won't
# recreate them when it next applies the map.
#
# This is a quick and dirty hack.  If we do something like this very often
# I'll refine it.
#
# This script is meant to be run in /home/lantern in the cloudmaster, and
# the text below should be replaced by the results of some salt query that
# returns the proxies you want to kill.  It is recommended that you disable
# the cloudmaster temporarily (for example, by just renaming cloudmaster.py
# to cloudmaster.bak and checking cloudmaster.log to make sure there are no
# requests in progress.

import os

import yaml


raw = """
fp-u3za9B5F1Onh:
    True
fp-L09JKWmjXdD1:
    True
fp-x79zyKCtj5EL:
    True
fp-7M4Qx1TDz9YP:
    True
fp-VjoW5zt5LWaJ:
    True
fp-cbtBOWFhN2vl:
    True
fp-BBvbINssPZKP:
    True
fp-L04mEwRRr8uO:
    True
fp-ciMy38y3PvId:
    True
fp-IjB5XrX8ktKJ:
    True
fp-ULm5a8l2O3DR:
    True
fp-ZszbYUPX10hO:
    True
fp-tvCzwX5fURXE:
    True
fp-oOGYBNsTSdMw:
    True
fp-U7V8BSpTHcPy:
    True
fp-Gt2ddKcwsTyc:
    True
"""

proxies = set([x.strip()[:-1]
               for x in raw.split()
               if x.startswith("fp-")])

d = yaml.load(file('map'))
for provider in ['do', 'aws']:
    for entry in d[provider][:]:
        name, = entry.keys()
        if name in proxies:
            d[provider].remove(entry)
            os.system("salt-cloud -yd %s" % name)
yaml.dump(d, file('map', 'w'))
