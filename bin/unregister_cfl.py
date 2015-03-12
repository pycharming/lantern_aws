#!/usr/bin/env python

"""Little utility to remove obsolete cloudflare records (e.g. from old
flashlight instances."""

import sys

import pyflare

import util


all_fls = set("""fl-singapore-001-19
fl-singapore-001-20
fl-singapore-008-8
fl-singapore-008-9""".split())

zone = 'getiantem.org'

roundrobins = [u'peers', u'fallbacks', u'roundrobin']

cf = pyflare.PyflareClient(*util.read_cf_credential())

import pprint

old_ips = set()

recs = list(cf.rec_load_all(zone))

for rec in recs:
    if str(rec['display_name']) in all_fls:
        old_ips.add(rec['content'])
        print "Deleting %s (%s)" % (rec['display_name'], rec['content'])
        print cf.rec_delete(zone, rec['rec_id'])

for rec in recs:
    if rec['display_name'] in roundrobins and rec['content'] in old_ips:
        print "now I would delete %s record for %s" % (rec['display_name'],
                                                       rec['content'])

print "Done!"

