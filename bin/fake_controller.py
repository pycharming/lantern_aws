#!/usr/bin/env python
"""To use this, set config.controller to some fake ID that no real controller
shares."""

import sys

import boto
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage

import config
import util


def trigger_launch():
    aws_id, aws_key = util.read_aws_credential()
    aws_creds = {'aws_access_key_id': aws_id,
                 'aws_secret_access_key': aws_key}
    sqs = boto.sqs.connect_to_region(config.region)
    req_q = sqs.get_queue("%s_request" % config.controller)
    notify_q = sqs.get_queue("notify_%s" % config.controller)
    for q in [req_q, notify_q]:
        q.set_message_class(JSONMessage)
    msg = JSONMessage()
    msg.set_body({'launch-invsrv-as': 'aranhoide@gmail.com',
                  'launch-refrtok':
                      '1/6Cvom_SuPfXG0dtrEoQgbozV18c0ctWOLA_P0_e7BEw'})
    print "Sending request..."
    req_q.write(msg)
    print "Awaiting response..."
    while True:
        msg = notify_q.read()
        notify_q.delete_message(msg)
        if msg is not None:
            print "Got message: %r" % msg.get_body()
            return
        sys.stdout.write(".")
        sys.stdout.flush()


if __name__ == '__main__':
    trigger_launch()
