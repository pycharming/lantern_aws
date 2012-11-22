#!/usr/bin/env python

import os
import shutil
import sys
import tempfile

import boto


def die(reason):
    print reason
    sys.exit(1)

if not (1 <= len(sys.argv) <= 3):
    die("Usage: %s [<security group> [<branch>]]" % sys.argv[0])

here = os.path.dirname(sys.argv[0])

if len(sys.argv) > 1:
    group = sys.argv[1]
else:
    group = 'lantern-peer'

if len(sys.argv) > 2:
    branch = sys.argv[2]
else:
    branch = 'master'

repo_root = os.path.join(here, "..")
repo_copy = tempfile.mkdtemp(prefix='update-group')

print "Cloning repository into", repo_copy, "..."
if os.system("git clone --bare %s %s" % (repo_root, repo_copy)):
    die("Failed to clone repository.")

print "Connecting to the EC2 endpoint..."
conn = boto.connect_ec2()

print "Looking up nodes in group", group, "..."
for reservation in conn.get_all_instances(filters={'group-name': group}):
    for instance in reservation.instances:
        if instance.state == 'running':
            print "Pushing to", instance.id, instance.ip_address, "..."
            if os.system("git push -f gitsalt@%s:config %s:master" %
                         (instance.ip_address, branch)):
                print "Push to", instance.id, instance.ip_address, "failed!"
            else:
                print "Done pushing."
        else:
            print "Ignoring", instance.state, "instance",
            print instance.id, instance.ip_address or "<no address>"

shutil.rmtree(repo_copy)

