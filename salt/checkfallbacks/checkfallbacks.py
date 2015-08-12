#!/usr/bin/env python

from email.mime.text import MIMEText
import json
import os
import smtplib
import subprocess
import sys
import yaml

import redis


redis_url = os.getenv('REDISCLOUD_PRODUCTION_URL') or "{{ pillar['cfgsrv_redis_url'] }}"
redis_shell = redis.from_url(redis_url)


#XXX: extract as a library.
def send_mail(from_, to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.sendmail(from_, [to], msg.as_string())
    s.close()

prefix = 'fallbacks-to-check'
try:
    local_version = file(prefix + '-version').read()
except IOError:
    local_version = None
remote_version = redis_shell.get('cfgbysrv:version')
if local_version != remote_version:
    json.dump([yaml.load(x).values()[0]
               for x in redis_shell.hgetall('cfgbysrv').values()],
              file(prefix + '.json', 'w'))
    file(prefix + '-version', 'w').write(remote_version)

cmd = subprocess.Popen("checkfallbacks -fallbacks %s.json -connections 20 | grep '\[failed fallback check\]'" % prefix,
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
