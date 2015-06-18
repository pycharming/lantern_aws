#!/usr/bin/env python

from email.mime.text import MIMEText
import os
import smtplib
import subprocess
import sys


#XXX: extract as a library.
def send_mail(from_, to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.sendmail(from_, [to], msg.as_string())
    s.close()

cmd = subprocess.Popen("checkfallbacks -fallbacks /home/lantern/fallbacks-to-check.json -connections 20 | grep '\[failed fallback check\]'",
                       shell=True,
                       stdout=subprocess.PIPE)
errors = list(cmd.stdout)
if errors:
    send_mail('lantern@production-cloudmaster',
              'fallback-alarms@getlantern.org',
              'Chained fallbacks failing to proxy',
              "".join(error[len('[failed fallback check] '):] + "\n"
                      for error in errors))
    for error in errors:
        print error
else:
    print "No errors."
