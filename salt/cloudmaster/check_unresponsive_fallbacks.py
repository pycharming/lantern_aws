#!/usr/bin/env python

import logging
import os
import sys

import boto.sqs
from boto.sqs.jsonmessage import JSONMessage
import salt.cli
import salt.client
import salt.key


AWS_REGION = "{{ grains['aws_region'] }}"
AWS_ID = "{{ pillar['aws_id'] }}"
AWS_KEY = "{{ pillar['aws_key'] }}"
aws_creds = {'aws_access_key_id': AWS_ID,
             'aws_secret_access_key': AWS_KEY}
CONTROLLER = "{{ grains['controller'] }}"

here = os.path.dirname(sys.argv[0]) if __name__ == '__main__' else __file__


def check():
    # Some black magic to get to salt's guts without going through the shell.
    sk = salt.cli.SaltKey()
    sk.parse_args()
    k = salt.key.Key(sk.config)
    all_fps = set(s for s in k.list_keys()['minions']
                  if s.startswith('fp-'))
    c = salt.client.LocalClient()
    responsive_fps = set(c.cmd('fp-*', 'test.ping').iterkeys())
    unresponsive_fps = all_fps - responsive_fps
    if unresponsive_fps:
        log.warn("We have unresponsive fallbacks!")
        for name in sorted(unresponsive_fps):
            log.warn("   " + name)
        sqs = boto.sqs.connect_to_region(AWS_REGION, **aws_creds)
        report_q = sqs.get_queue("notify_%s" % CONTROLLER)
        msg = JSONMessage()
        msg.set_body({'fp-alarm': "Unresponsive fallbacks",
                      'instance-id': " ".join(sorted(unresponsive_fps)),
                      'send-email': True,
                      # These fields are expected by the controller, but they
                      # make no sense in this case.
                      'user': "n/a",
                      'ip': "n/a",
                      'port': "n/a"})
        report_q.write(msg)
        log.info("Reported.")
    else:
        log.info("No unresponsive fallbacks.")


if __name__ == '__main__':
    # I have to do all this crap because salt hijacks the root logger.
    log = logging.getLogger('check_unresponsive_fallbacks')
    log.setLevel(logging.INFO)
    handler = logging.FileHandler(os.path.join(here, "check_unresponsive_fallbacks.log"))
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
    log.addHandler(handler)
    log.info("check starting...")
    try:
        check()
    except Exception as e:
        log.exception(e)
    log.info("check done.")


