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
            # WARNING: Even if we eventually stop building installers in the
            # cloudmaster we should not downgrade it to a micro instance.
            # A micro instance will still run out of memory when trying to
            # spawn peers (this is probably a bug in salt-cloud?)
            instance_type='m1.small',
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
    while init_dir('/srv/salt'):
        time.sleep(delay)
        delay *= 1.5
        print "Retrying..."
    print
    print "Initializing /home/lantern..."
    init_dir('/home/lantern')
    print
    print "Uploading salt configuration..."
    update.rsync_salt()
    print "Setting cloudmaster minion config..."
    upload_cloudmaster_minion_config()
    print "Uploading secrets..."
    update.upload_secrets()
    print "Copying bootstrap file..."
    os.system("scp -i %s %s ubuntu@%s:"
              % (key_path, here.bootstrap_path, ins.ip_address))
    print "Bootstrapping..."
    util.ssh_cloudmaster("sudo ./bootstrap.bash", ".log")
    print
    print "Done launching."
    update.print_errors()

def init_dir(path):
    return util.ssh_cloudmaster("sudo mkdir %s ; sudo chown ubuntu:ubuntu %s"
                                % (path, path))

def upload_cloudmaster_minion_config():
    key_path = region.get_key_path()
    address = util.get_address()
    init_dir("/etc/salt")
    aws_id, aws_key = util.read_aws_credential()
    do_id, do_key = util.read_do_credential()
    util.ssh_cloudmaster((r"""(echo "master: salt" """
                          + r""" && echo "grains:" """
                          + r""" && echo "    aws_id: %s" """
                          + r""" && echo "    aws_key: \"%s\"" """
                          + r""" && echo "    aws_region: %s " """
                          + r""" && echo "    aws_ami: %s " """
                          + r""" && echo "    do_id: %s " """
                          + r""" && echo "    do_key: %s " """
                          + r""" && echo "    do_region: %s " """
                          + r""" && echo "    controller: %s " """
                          + r""" ) > /etc/salt/minion""")
                         % (aws_id,
                            aws_key,
                            config.aws_region,
                            region.get_ami(),
                            do_id,
                            do_key,
                            config.do_region,
                            config.controller))


if __name__ == '__main__':
    launch_cloudmaster()
