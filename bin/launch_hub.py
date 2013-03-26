#!/usr/bin/env python

from itertools import *
import getpass
import socket
import os
import time
import traceback
import sys

import boto.ec2

from bin_dir import bin_dir


amis = {"ap-northeast-1": "ami-60c77761",
        "ap-southeast-1": "ami-a4ca8df6",
        "eu-west-1": "ami-e7e8d393",
        "sa-east-1": "ami-8cd80691",
        "us-east-1": "ami-a29943cb",
        "us-west-1": "ami-87712ac2",
        "us-west-2": "ami-20800c10"}

region = 'us-east-1'
keypair_dir = os.path.expanduser('~/.lantern-keypairs')

def get_key(conn):
    key_prefix = 'lantern-%s-%s-%s' % (region,
                                       socket.gethostname(),
                                       getpass.getuser())
    if not os.path.exists(keypair_dir):
        os.makedirs(keypair_dir)
    for i in count(1):
        key_name = '%s-%s' % (key_prefix, i)
        key_path = os.path.join(keypair_dir, key_name + '.pem')
        if os.path.exists(key_path):
            break
        try:
            print "Trying to create new keypair '%s'" % key_name
            key_pair = conn.create_key_pair(key_name)
            if key_pair.save(keypair_dir):
                break
        except:
            traceback.print_exc()
    return key_name, key_path

here = bin_dir()
salt_states_path = os.path.join(here, '..', 'salt')
bootstrap_path = os.path.join(here, '..', 'etc','bootstrap.bash')

def launch_instance(name):
    conn = boto.ec2.connect_to_region(region)
    key_name, key_path = get_key(conn)
    print "Creating instance..."
    reservation = conn.run_instances(
            amis[region],
            key_name=key_name,
            instance_type='t1.micro',
            #XXX: create this security group if not already there.
            security_groups=['free-for-all'])
    print "Waiting for instance to run..."
    delay = 1
    while True:
        ins, = reservation.instances
        if ins.state == 'running':
            break
        time.sleep(delay)
        delay *= 1.5
        reservation, = conn.get_all_instances(instance_ids=[ins.id])
    print "Setting instance name for %s ..." % ins.ip_address
    conn.create_tags([ins.id], {'Name': name})

    print
    print "Trying to connect to server..."
    print "(You may see some connection refusals; this is normal.)"
    print
    delay = 1
    while os.system(("rsync -e 'ssh -o StrictHostKeyChecking=no -i %s'"
                     + " -az %s/ ubuntu@%s:salt")
                    % (key_path, salt_states_path, ins.ip_address)):
        time.sleep(delay)
        delay *= 1.5
        print "Retrying..."
    print "`rsync`ed successfuly!"
    print
    print "Copying bootstrap file..."
    print
    os.system("scp -i %s %s ubuntu@%s:"
              % (key_path, bootstrap_path, ins.ip_address))
    print
    print "Bootstrapping..."
    print
    os.system(("ssh -i %s ubuntu@%s"
               + " 'sudo rm -rf /srv/salt"
               + " && sudo mv salt /srv"
               + " && sudo ./bootstrap.bash'")
              % (key_path, ins.ip_address))

    print "launch_hub done."

if __name__ == '__main__':
    if len(sys.argv) == 2:
        launch_instance(sys.argv[1])
    else:
        print "Usage: %s <name>" % sys.argv[0]
        sys.exit(1)
