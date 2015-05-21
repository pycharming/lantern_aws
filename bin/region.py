from itertools import *
import os

try:
    import boto.ec2
except ImportError:
    print
    print "No boto module found."
    print "try `pip install boto`"
    print
    import sys
    sys.exit(1)

import config
import here
import util


amis = {"ap-northeast-1": "ami-60c77761",
        "ap-southeast-1": "ami-a4ca8df6",
        "eu-west-1": "ami-e7e8d393",
        "sa-east-1": "ami-8cd80691",
        "us-east-1": "ami-a29943cb",
        "us-west-1": "ami-87712ac2",
        "us-west-2": "ami-20800c10"}

def get_ami():
    return amis[config.aws_region]

@util.memoized
def connect():
    aws_id, aws_key = util.read_aws_credential()
    print "Connecting to region %s..." % config.aws_region
    return boto.ec2.connect_to_region(config.aws_region,
                                      aws_access_key_id=aws_id,
                                      aws_secret_access_key=aws_key)

def assure_security_group_present():
    try:
        group = connect().create_security_group(
                config.free_for_all_sg_name,
                "Promiscuous security group"
                 + " for machines with local firewalls.")
    except boto.exception.EC2ResponseError as e:
        if e.error_code == 'InvalidGroup.Duplicate':
            print "Security group already exists."
            return
        else:
            raise
    group.authorize('tcp', 0, 65535, '0.0.0.0/0')
    group.authorize('udp', 0, 65535, '0.0.0.0/0')
    # -1 is a wildcard for ICMP, so this is effectively authorizing ALL types.
    group.authorize('icmp', -1, -1, '0.0.0.0/0')
    print "Created security group."
