#!/usr/bin/env python

import os
import time
import sys

import config
import here
import region
import update
import util


def launch_cloudmaster():
    util.set_secret_permissions()
    conn = region.connect()
    print "Checking/creating prerequisites..."
    region.assure_security_group_present()
    print "Creating instance..."
    reservation = conn.run_instances(
            region.get_ami(),
            key_name='lantern',
            instance_type='t1.micro',
            security_groups=[config.free_for_all_sg_name])
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
    conn.create_tags([ins.id], {'Name': config.cloudmaster_name})
    print
    print "Trying to connect to server..."
    print "(You may see some connection refusals; this is normal.)"
    print
    key_path = region.get_key_path()
    delay = 1
    while os.system(("ssh -o StrictHostKeyChecking=no -i %s ubuntu@%s "
                     + " 'sudo mkdir /srv/salt "
                     + " && sudo chown ubuntu:ubuntu /srv/salt'")
                     % (key_path, ins.ip_address)):
        time.sleep(delay)
        delay *= 1.5
        print "Retrying..."
    print
    print "Uploading salt configuration..."
    update.rsync_salt()
    print "Setting cloudmaster minion config..."
    update.upload_cloudmaster_minion_config()
    print "Copying bootstrap file..."
    os.system("scp -i %s %s ubuntu@%s:"
              % (key_path, here.bootstrap_path, ins.ip_address))
    print "Bootstrapping..."
    os.system("ssh -i %s ubuntu@%s 'sudo ./bootstrap.bash' | tee .log"
              % (key_path, ins.ip_address))
    print
    print "Done launching. Any prints below may be caused by errors:"
    print
    os.system("grep -i error .log")
    os.system("grep False .log")


if __name__ == '__main__':
    launch_cloudmaster()
