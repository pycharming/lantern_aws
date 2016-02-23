import datetime
from email.mime.text import MIMEText
import os
import smtplib
import subprocess
import time
import traceback

from redis_util import redis_shell
import requests

import vps_util

auth_token = "{{ pillar['cfgsrv_token'] }}"
instance_id = "{{ grains['id'] }}"
region = vps_util.region_by_name(instance_id)

# {% from 'ip.sls' import external_ip %}
ip = "{{ external_ip(grains) }}"
close_flag_filename = "server_closed"
retire_flag_filename = "server_retired"


def send_mail(from_, to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.sendmail(from_, [to], msg.as_string())
    s.close()

def send_alarm(subject, body):
    send_mail('lantern@%s' % instance_id,
              'fallback-alarms@getlantern.org',
              subject,
              "Chained fallback %s (%s) reports: %s" % (instance_id,
                                                        ip,
                                                        body))

def flag_as_done(flag_filename):
    file(flag_filename, 'w').write(str(datetime.datetime.utcnow()))

def close_server(msg):
    if os.path.exists(close_flag_filename):
        print "Not closing myself again."
        return
    srvid = redis_shell.hget('srvip->srv', ip)
    skey = region + ":slices"
    score = redis_shell.zscore(skey, srvid)
    if not score:
        print "I was not open, so I won't try to close myself."
        flag_as_done(close_flag_filename)
        return
    p = redis_shell.pipeline()
    p.zrem(skey, srvid)
    p.zadd(skey, ('<empty:%s>' % score), score)
    p.execute()
    flag_as_done(close_flag_filename)
    send_alarm("Chained proxy closed", " closed because I " + msg)

def retire_server(msg):
    if os.path.exists(retire_flag_filename):
        print "Not retiring myself again."
        return
    redis_shell.lpush(vps_util.my_cm() + ':retireq', '%s|%s' % (instance_id, ip))
    flag_as_done(retire_flag_filename)
    send_alarm("Chained proxy RETIRED",
               " retired because I " + msg)
