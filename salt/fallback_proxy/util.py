import datetime
from email.mime.text import MIMEText
import os
import smtplib
import time

import redis
import requests


auth_token = "{{ pillar['cfgsrv_token'] }}"
instance_id = "{{ grains['id'] }}"
if instance_id.startswith('fp-nl-'):
    dc = 'doams3'
elif instance_id.startswith('fp-jp-'):
    dc = 'vltok1'
else:
    assert False, repr(instance_id)

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
    file(flag_filename, 'w').write(str(datetime.datetime.now()))

def split_server(msg, retire=False):
    if retire:
        data = {'dislodge-users?': 'true'}
        flag_filename = retire_flag_filename
        # Uppercase so it catches our eye in the fallback-alarms list. As of
        # this writing, we need to manually unregister these fallbacks from the
        # list of ones to check and then shut them down.
        participle = "RETIRED"
        infinitive = "RETIRE"
    else:
        data = {}
        flag_filename = split_flag_filename
        participle = infinitive = 'split'
    if os.path.exists(flag_filename):
        return
    for attempt in xrange(7):
        resp = requests.post("https://config.getiantem.org/split-server",
                             headers={"X-Lantern-Auth-Token": auth_token},
                             data=data)
        if resp.status_code == 200:
            flag_as_done(flag_filename)
            send_alarm("Chained fallback " + participle,
                       participle + " because I " + msg)
            break
        time.sleep(2 << attempt)
    else:
        r = redis.from_url(os.getenv('REDIS_URL'))
        srvs = r.zrangebyscore(dc + ':slices', '-inf', '+inf')
        for srv in srvs:
            cfg = r.hget('cfgbysrv', srv)
            cfgip = cfg.split('|')[0]
            if cfgip == ip:
                send_alarm("Unable to %s chained fallback" % infinitive,
                           "I tried to %s myself because I %s, but I couldn't." % (infinitive, msg))
                break
        else:
            # This server is not open so it can't be split. We only check this
            # after having tried because this check is expensive and rarely
            # needed.
            flag_as_done(flag_filename)
    if retire:
        r = redis.from_url(os.getenv('REDIS_URL'))
        r.lpush(dc + ':retireq', '%s|%s' % (instance_id, ip))
        flag_as_done(flag_filename)
