import datetime
from email.mime.text import MIMEText
import os
import smtplib
import time

import requests


auth_token = "{{ pillar['cfgsrv_token'] }}"
instance_id = "{{ grains['id'] }}"
# {% from 'ip.sls' import external_ip %}
ip = "{{ external_ip(grains) }}"
flag_filename = "server_split"


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

def split_server(msg):
    if os.path.exists(flag_filename):
        return
    for attempt in xrange(7):
        resp = requests.post("https://config.getiantem.org/split-server",
                             headers={"X-Lantern-Auth-Token": auth_token})
        if resp.status_code == 200:
            file(flag_filename, 'w').write(str(datetime.datetime.now()))
            send_alarm("Chained fallback split",
                       "split because I " + msg)
            return
        time.sleep(2 << attempt)
    else:
        send_alarm("Unable to split chained fallback",
                   "I tried to split myself because I %s, but I couldn't." % msg)
        return 'failure'
