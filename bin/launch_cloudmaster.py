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
    delay = 1
    while init_dir('/srv/salt'):
        time.sleep(delay)
        delay *= 1.5
        print "Retrying..."
    print
    print "Initializing directories..."
    init_dir('/srv/pillar')
    init_dir('/home/lantern')
    init_dir('/etc/salt')
    print
    print "Uploading pillars..."
    update.upload_pillars()
    print "Setting cloudmaster minion config..."
    update.upload_cloudmaster_minion_config()
    print "Uploading salt configuration..."
    update.rsync_salt()
    print "Uploading secrets..."
    update.upload_secrets()
    print "Copying bootstrap file..."
    os.system("scp -i %s %s ubuntu@%s:"
              % (config.key_path, here.bootstrap_path, ins.ip_address))
    print "Bootstrapping..."
    util.ssh_cloudmaster("sudo SALT_VERSION=%s ./bootstrap.bash"
                            % config.salt_version,
                         ".log")
    print
    print "Done launching."
    update.print_errors()

def init_dir(path):
    return util.ssh_cloudmaster("sudo mkdir %s ; sudo chown ubuntu:ubuntu %s"
                                % (path, path))


if __name__ == '__main__':
    launch_cloudmaster()
