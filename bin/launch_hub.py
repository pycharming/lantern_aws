#!/usr/bin/env python

import os
import time
import sys

import here
import region
import util


def launch_instance(name):
    util.set_secret_permissions()
    conn = region.connect()
    print "Checking/creating prerequisites..."
    key_path = os.path.join(here.secrets_path,
                            'lantern_aws',
                            region.get_region() + ".pem")
    region.assure_security_group_present(conn)
    print "Creating instance..."
    reservation = conn.run_instances(
            region.get_ami(),
            key_name='lantern',
            instance_type='t1.micro',
            security_groups=[region.free_for_all_sg_name])
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
    while util.rsync(key_path, ins.ip_address, remote_path='salt'):
        time.sleep(delay)
        delay *= 1.5
        print "Retrying..."
    print
    print "Copying bootstrap file..."
    print
    os.system("scp -i %s %s ubuntu@%s:"
              % (key_path, here.bootstrap_path, ins.ip_address))
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
