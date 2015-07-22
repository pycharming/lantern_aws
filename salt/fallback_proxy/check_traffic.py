#!/usr/bin/env python

from __future__ import division

from datetime import datetime
from email.mime.text import MIMEText
import smtplib
import time

import psutil
import yaml


# Allow to configure this in a Jinja template, for DRY.
period_minutes = "{{ traffic_check_period_minutes }}"
# But also let me test it locally.
if period_minutes.startswith("{"):
    period_minutes = "5"
period = int(period_minutes) * 60

instance_id = "{{ grains['id'] }}"
# {% from 'ip.sls' import external_ip %}
ip = "{{ external_ip(grains) }}"

traffic_log_filename = "traffic_log.yaml"

day = 24 * 60 * 60
alarm_threshold = 0.1


#XXX: extract as a library.
def send_mail(from_, to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.sendmail(from_, [to], msg.as_string())
    s.close()

def alarm(proportion):
    send_mail('lantern@%s' % instance_id,
              'fallback-alarms@getlantern.org',
              'Low traffic in chained fallback',
              "Fallback proxy %s (%s) is pushing %.2f%%"
              " of its usual throughput this time of the day"
              % (instance_id, ip, proportion * 100))
def load():
    try:
        return yaml.load(file(traffic_log_filename))
    except IOError:
        return {'bps': {}}

def save(d):
    yaml.dump(d, file(traffic_log_filename, 'w'))

def run():
    print "%s: check_traffic starting..." % datetime.now()
    d = load()
    try:
        last_mark = d.get('last_mark')
        last_time = d.get('last_time')
        new_time = d['last_time'] = int(time.time())
        new_mark = d['last_mark'] = psutil.net_io_counters().bytes_sent
        if last_mark is None:
            print "No last_mark"
            return
        if last_time is None:
            print "No last_time"
            return
        if last_mark > new_mark:
            print "Reset mark (rebooted?)"
            return
        if new_time - last_time > period + 60:
            print "Too much time between samples"
            return
        bps = (new_mark - last_mark) / (new_time - last_time)
        bucket = (new_time % day) // period
        print "bucket is", bucket
        bps_avg = d['bps'].get(bucket)
        if bps_avg is None:
            print "No old average for this bucket"
            d['bps'][bucket] = bps
            return
        d['bps'][bucket] = (bps_avg + bps) / 2
        if bps_avg == 0.0:
            print "Old average was zero"
            return
        proportion = bps / bps_avg
        if proportion < alarm_threshold:
            print "proportion %s below threshold; sending alarm!" % proportion
            alarm(proportion)
        else:
            print "proportion %s is alright." % proportion
    finally:
        save(d)
        print "Done."


if __name__ == '__main__':
    run()
