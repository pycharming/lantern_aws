#!/usr/bin/env python

from email.mime.text import MIMEText
import os
import smtplib
import sys

import redis
from vultr.vultr import Vultr

from redis_util import redis_shell
import vps_util


def vpss_from_cm(cm):
    try:
        local_version = file(cm + '_vpss_version').read()
    except IOError:
        local_version = None
    remote_version = redis_shell.get(cm + ':vpss:version')
    if local_version == remote_version:
        return set(map(str.strip, file(cm + '_vpss')))
    else:
        ret = redis_shell.lrange(cm + ':vpss', 0, -1)
        file(cm + '_vpss', 'w').write('\n'.join(ret))
        file(cm + '_vpss_version', 'w').write(remote_version)
        return set(ret)

def in_production(name):
    return (not name.startswith('fp-')
            or vps_util.cm_by_name(name) in ['doams3', 'dosgp1'])

expected_do = vpss_from_cm('doams3') | vpss_from_cm('dosgp1')
expected_vultr = vpss_from_cm('vltok1') | vpss_from_cm('vlfra1')

actual_do = set(v.name for v in vps_util.vps_shell('do').all_vpss()
                if in_production(v.name))
actual_vultr = set(v.name for v in vps_util.vps_shell('vl').all_vpss())

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
