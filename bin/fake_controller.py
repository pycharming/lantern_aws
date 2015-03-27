#!/usr/bin/env python
"""To use this, set config.controller to some fake ID that no real controller
shares."""

import sys

import boto
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage

import config
import util
import json


def launch_fp(fpid, pillars='{}', profile=config.default_profile):
    send_message({'launch-fp': fpid,
                  'profile': profile,
                  #XXX: pillars
                  'launch-pillars': json.loads(pillars)})

def launch_fl(flid, profile=config.default_profile):
    send_message({'launch-fl': flid, 'profile': profile})

def launch_wd(flid, profile=config.default_profile):
    send_message({'launch-wd': flid, 'profile': profile})

def launch_ps(flid, profile=config.default_profile):
    send_message({'launch-ps': flid, 'profile': profile})

def launch_au(flid, profile=config.default_profile):
    send_message({'launch-au': flid, 'profile': profile})

def kill_fl(flid):
    send_message({'shutdown-fl': flid})

def kill_fp(fpid):
    send_message({'shutdown-fp': fpid})

def send_message(d):
    aws_id, aws_key = util.read_aws_credential()
    aws_creds = {'aws_access_key_id': aws_id,
                 'aws_secret_access_key': aws_key}
    sqs = boto.sqs.connect_to_region(config.aws_region, **aws_creds)
    req_q = sqs.get_queue("%s_request" % config.controller)
    req_q.set_message_class(JSONMessage)
    msg = JSONMessage()
    msg.set_body(d)
    print "Sending request..."
    req_q.write(msg)
    print "Sent."

def print_usage():
    print "Usage: %s (launch-fl|kill-fl|launch-wd|launch-ps) <id> [<profile>='%s'] | (launch-fp|kill-fp) <id> [{pillar_key: pillar_value[, pillar_key: pillar_value]...} [<profile>='%s']]" % (sys.argv[0], config.default_profile, config.default_profile)

if __name__ == '__main__':
    try:
        cmd = sys.argv[1]
        if cmd == 'launch-fl':
            launch_fl(*sys.argv[2:])
        elif cmd == 'launch-wd':
            launch_wd(*sys.argv[2:])
        elif cmd == 'launch-ps':
            launch_ps(*sys.argv[2:])
        elif cmd == 'launch-au':
            launch_au(*sys.argv[2:])
        elif cmd == 'kill-fl':
            kill_fl(sys.argv[2])
        else:
            id_ = sys.argv[2]
            if cmd == 'launch-fp':
                if len(sys.argv) > 3:
                    pillars = sys.argv[3]
                else:
                    pillars = '{}'
                if len(sys.argv) > 4:
                    profile = sys.argv[4]
                else:
                    profile = config.default_profile
                launch_fp(id_, pillars, profile)
            elif cmd == 'kill-fp':
                kill_fp(id_)
            else:
                print_usage()
    except (ValueError, IndexError):
        print_usage()
