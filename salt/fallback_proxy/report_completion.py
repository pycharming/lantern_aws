#!/usr/bin/env python

from base64 import b64decode
from cPickle import loads
import logging
import os.path
from functools import wraps

import boto.sqs
from boto.sqs.jsonmessage import JSONMessage


# DRY warning: ../cloudmaster/cloudmaster.py
USERID = "{{ pillar['user'] }}"
AWS_REGION = "{{ grains['aws_region'] }}"
AWS_ID = "{{ pillar['aws_id'] }}"
AWS_KEY = "{{ pillar['aws_key'] }}"
CONTROLLER = "{{ grains['controller'] }}"
SQSMSG = "{{ pillar['sqs_msg'] }}"
aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}


def log_exceptions(f):
    @wraps(f)
    def deco(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception, e:
            logging.exception(e)
            raise
    return deco

@log_exceptions
def report_completion():
    installer_location = file('/home/lantern/uploaded_wrappers').read()
    sqs = boto.sqs.connect_to_region(AWS_REGION, **aws_creds)
    logging.info("Reporting installers for %s are ready at %s."
                 % (clip_email(USERID), installer_location))
    ctrl_req_q = sqs.get_queue("%s_request" % CONTROLLER)
    ctrl_notify_q = sqs.get_queue("notify_%s" % CONTROLLER)
    msg = JSONMessage()
    msg.set_body(
            {'invsrvup-user': USERID,
             'invsrvup-insloc': installer_location})
    ctrl_notify_q.write(msg)
    DEL_FLAG = '/home/lantern/deleted_sqs_message'
    if not os.path.exists(DEL_FLAG):
        to_delete = loads(b64decode(SQSMSG))
        ctrl_req_q.delete_message(to_delete)
        file(DEL_FLAG, 'w').write('OK')
    file('/home/lantern/reported_completion', 'w').write('OK')

def clip_email(email):
    at_index = email.find('@')
    return '%s...%s' % (email[:1], email[at_index-2:at_index])


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename='/home/lantern/report_completion.log',
                        format='%(levelname)-8s %(message)s')
    report_completion()
