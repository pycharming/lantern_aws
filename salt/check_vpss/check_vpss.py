#!/usr/bin/env python

from email.mime.text import MIMEText
import os
import smtplib
import sys

import digitalocean
from vultr.vultr import Vultr


here = os.path.dirname(sys.argv[0])

do_token = os.getenv("DO_TOKEN") or "{{ pillar['do_token'] }}"
vultr_apikey = os.getenv("VULTR_APIKEY") or "{{ pillar['vultr_apikey'] }}"

do_shell = digitalocean.Manager(token=do_token)
vultr_shell = Vultr(vultr_apikey)

def vpss_from_file(filename):
    return set(filter(None,
                      (line.split("#", 1)[0].strip()
                       for line in file(os.path.join(here, filename)).read().split('\n'))))

expected_do = vpss_from_file("do_vpss")
expected_vultr = vpss_from_file("vultr_vpss")

actual_do = set([d.name for d in do_shell.get_all_droplets()])
actual_vultr = set([d['label']
                    for d in vultr_shell.server_list(None).itervalues()])

errors = []
for caption, vpss in [("Missing DO droplets", expected_do - actual_do),
                      ("Unexpected DO droplets", actual_do - expected_do),
                      ("Missing Vultr VPSs", expected_vultr - actual_vultr),
                      ("Unexpected Vultr VPSs", actual_vultr - expected_vultr)]:
    if vpss:
        errors.append(caption + ": " + ", ".join(sorted(vpss)))

def send_mail(from_, to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.sendmail(from_, [to], msg.as_string())
    s.close()

if errors:
    send_mail('lantern@production-cloudmaster',
              'fallback-alarms@getlantern.org',
              'Mismatch in VPS list',
              "".join(error + "\n" for error in errors))
    for error in errors:
        print "ERROR: ", error
else:
    print "No errors."
