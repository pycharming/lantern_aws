from itertools import *
import os

import boto.ec2


default_region = 'us-east-1'

amis = {"ap-northeast-1": "ami-60c77761",
        "ap-southeast-1": "ami-a4ca8df6",
        "eu-west-1": "ami-e7e8d393",
        "sa-east-1": "ami-8cd80691",
        "us-east-1": "ami-a29943cb",
        "us-west-1": "ami-87712ac2",
        "us-west-2": "ami-20800c10"}

def get_region(region=None):
    return region or os.getenv('EC2_REGION', default_region)

def get_ami(region=None):
    return amis[get_region(region)]

def connect(region=None):
    region = get_region(region)
    print "Connecting to region %s..." % region
    return boto.ec2.connect_to_region(region)

def get_key(conn=None, region=None):
    region = get_region(region)
    return 'lantern',
    key_prefix = 'lantern-%s-%s-%s' % (region,
                                       socket.gethostname(),
                                       getpass.getuser())
    if not os.path.exists(keypair_dir):
        os.makedirs(keypair_dir)
    conn = None
    for i in count(1):
        key_name = '%s-%s' % (key_prefix, i)
        key_path = os.path.join(keypair_dir, key_name + '.pem')
        if os.path.exists(key_path):
            break
        try:
            print "Trying to create new keypair '%s'" % key_name
            key_pair = (conn or connect(region)).create_key_pair(key_name)
            if key_pair.save(keypair_dir):
                break
        except:
            traceback.print_exc()
    return key_name, key_path

free_for_all_sg_name = 'free-for-all'

def assure_security_group_present(conn):
    try:
        group = conn.create_security_group(
                free_for_all_sg_name,
                ("Promiscuous security group"
                 + " for machines with local firewalls."))
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
