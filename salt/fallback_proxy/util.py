import datetime
from email.mime.text import MIMEText
import os
import smtplib
import subprocess
import time
import traceback

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
    r = redis.from_url(os.getenv('REDIS_URL'))
    srvid = r.hget('srvbysrvip', ip)
    if not srvid or not r.zrank(dc + ':slices', srvid):
        # This server is not open so it can't be split. We only check this
        # after having tried because this is rarely needed.
        print "I was not open, so I won't try to split myself."
        flag_as_done(split_flag_filename)
    else:
        for attempt in xrange(7):
            try:
                resp = subprocess.check_output(['curl',
                                                '-i',
                                                '-X', 'POST',
                                                '-H', 'X-Lantern-Auth-Token: ' + auth_token,
                                                'https://config.getiantem.org/split-server'])
                if "Server successfully split" in resp:
                    flag_as_done(split_flag_filename)
                    send_alarm("Chained fallback " + participle,
                            participle + " because I " + msg)
                    break
                else:
                    print "Bad response:"
                    print resp
            except:
                traceback.print_exc()
            time.sleep(2 << attempt)
        else:
            send_alarm("Unable to %s chained fallback" % infinitive,
                        "I tried to %s myself because I %s, but I couldn't." % (infinitive, msg))
    if retire:
        r.lpush(dc + ':retireq', '%s|%s' % (instance_id, ip))
        flag_as_done(retire_flag_filename)
