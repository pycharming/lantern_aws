import json
import os
import sys

try:
    import redis_util
except ImportError:
    # Some VPSs don't have redis configured. We still want to be able to send
    # slack notifications from those.
    print >> sys.stderr, "Couldn't import redis_util; alert() won't work."
import requests


instance_id = "{{ grains['id'] }}"
# {% from 'ip.sls' import external_ip %}
ip = "{{ external_ip(grains) }}"
url = os.environ.get('SLACK_WEBHOOK_URL')

# Allow for testing in developer machines. You still need to set
# SLACK_WEBHOOK_URL locally, of course.
if instance_id.startswith('{{'):
    import getpass
    instance_id = getpass.getuser()
    ip = "<developer machine>"

def send_to_slack(title, text, color='warning', channel=None):
    text = "%s (%s) reports:\n%s" % (instance_id, ip, text)
    payload = {"fallback": title + '\n' + text,
               "color": color,
               "title": title,
               "text": text,
               "mrkdwn_in": ['text']}
    data = {'attachments': [payload]}
    if channel:
        data['channel'] = channel
    requests.post(url,
                  headers={'content-type': 'application/json'},
                  data=json.dumps(data))

def alert(type, details, title=None, text=None, color='warning', pipeline=None):
    """
    Shortcut for logging an alert and sending it to slack.

    Prepends name and IP of reporting machine in text, inserts them in details.
    """
    if not title:
        title = type.replace("-", " ").capitalize()
    if not text:
        text = str(details)
    details_ = details.copy()
    details_['name'] = instance_id
    details_['ip'] = ip
    redis_util.log2redis({'alert': type, 'details': details_}, pipeline=pipeline)
    send_to_slack(title, text, color)
