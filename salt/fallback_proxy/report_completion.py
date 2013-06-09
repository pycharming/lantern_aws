#!/usr/bin/env python

import boto
from boto.sqs.jsonmessage import JSONMessage

def report_completion():
    logging.info("Reporting installers for %s are ready at %s."
                 % (clip_email(email), task.installer_location))
    msg = JSONMessage()
    msg.set_body(
            {'invsrvup-user': email,
             'invsrvup-insloc': task.installer_location})
    ctrl_notify_q.write(msg)
    ctrl_req_q.delete_message(task.message)

#XXX: duplicated; factor out
def clip_email(email):
    at_index = email.find('@')
    return '%s...%s' % (email[:1], email[at_index-2:at_index])
