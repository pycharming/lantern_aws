import json
import os

import redis_util
import requests


instance_id = "{{ grains['id'] }}"
# {% from 'ip.sls' import external_ip %}
ip = "{{ external_ip(grains) }}"
url = os.environ.get('SLACK_WEBHOOK_URL')


def send_to_slack(title, text, color='warning'):
    payload = {"fallback": title + '\n' + text,
               "color": color,
               "title": title,
               "text": text,
               "mrkdwn_in": ['text']}
    requests.post(url,
                  headers={'content-type': 'application/json'},
                  data=json.dumps({'attachments': [payload]}))

def alert(type, details, title=None, text=None, color='warning', pipeline=None):
    """
    Shortcut for logging an alert and sending it to slack.

    Prepends name and IP of reporting machine in text, inserts them in details.
    """
    if not title:
        title = type.replace("-", " ").capitalize()
    if not text:
        text = str(details)
    text = "%s (%s) reports:\n%s" % (instance_id, ip, text)
    details_ = details.copy()
    details_['name'] = instance_id
    details_['ip'] = ip
    redis_util.log2redis({'alert': type, 'details': details_}, pipeline=pipeline)
    send_to_slack(title, text, color)
