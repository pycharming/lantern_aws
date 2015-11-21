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
split_flag_filename = "server_split"
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

def split_server(msg):
    if os.path.exists(split_flag_filename):
        print "Not splitting myself again."
        return
    srvid = redis_shell.hget('srvip->srv', ip)
    if not srvid or not redis_shell.zrank(region + ':slices',
                                          srvid):
        print "I was not open, so I won't try to split myself."
        flag_as_done(split_flag_filename)
        return
    for attempt in xrange(7):
        try:
            resp = subprocess.check_output(['curl',
                                            '-i',
                                            '-X', 'POST',
                                            '-H', 'X-Lantern-Auth-Token: ' + auth_token,
                                            'https://config.getiantem.org/split-server'])
            if "Server successfully split" in resp:
                flag_as_done(split_flag_filename)
                send_alarm("Chained proxy split",
                            " split because I " + msg)
                break
            else:
                print "Bad response:"
                print resp
        except:
            traceback.print_exc()
        time.sleep(2 << attempt)
    else:
        send_alarm("Unable to split chained fallback",
                    "I tried to split myself because I %s, but I couldn't." % msg)

def retire_server(msg):
    if os.path.exists(retire_flag_filename):
        print "Not retiring myself again."
        return
    redis_shell.lpush(vps_util.my_cm() + ':retireq', '%s|%s' % (instance_id, ip))
    flag_as_done(retire_flag_filename)
    send_alarm("Chained proxy RETIRED",
               " retired because I " + msg)
