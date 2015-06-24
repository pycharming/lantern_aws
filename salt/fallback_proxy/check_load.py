#!/usr/bin/env python

{% from 'ip.sls' import external_ip %}

import datetime
from email.mime.text import MIMEText
import os
import smtplib
import time

import requests


auth_token = "{{ pillar['cfgsrv_token'] }}"
flag_filename = "server_split"
instance_id = "{{ grains['id'] }}"
ip = "{{ external_ip(grains) }}"
report_threshold = 0.8
split_threshold = 0.7


#XXX: extract as a library.
def send_mail(from_, to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.sendmail(from_, [to], msg.as_string())
    s.close()

_, _, la15m = os.getloadavg()

print "starting..."

if la15m > report_threshold:
    print "report threshold surpassed; notifying..."
    send_mail('lantern@%s' % instance_id,
              'fallback-alarms@getlantern.org',
              'Chained fallback high load',
              "Fallback proxy %s (%s) has load average %s" % (instance_id,
                                                              ip,
                                                              la15m))

if not os.path.exists(flag_filename) and la15m > split_threshold:
    for attempt in xrange(7):
        resp = requests.post("https://config.getiantem.org/split-server",
                             headers={"X-Lantern-Auth-Token": auth_token})
        if resp.status_code == 200:
            file(flag_filename, 'w').write(str(datetime.datetime.now()))
            print "Server split."
            send_mail('lantern@production-cloudmaster',
                      'fallback-alarms@getlantern.org',
                      'Chained fallback split',
                      ("Fallback proxy %s (%s) has just been split"
                       + " after reaching load average %s.") % (instance_id,
                                                                ip,
                                                                la15m))
            break
        print "Couldn't split, %s: %s" % (resp.status_code, resp.text)
        print "waiting to retry..."
        time.sleep(2 << attempt)
        print "Retrying..."
    else:
        send_mail('lantern@%s' % instance_id,
                  'fallback-alarms@getlantern.org',
                  'Unable to split chained fallback',
                  ("Fallback proxy %s (%s) has reached load average %s"
                   + " but I couldn't split it.") % (instance_id,
                                                     ip,
                                                     la15m))
        print "Couldn't split at all; giving up for now."

print "... done."
