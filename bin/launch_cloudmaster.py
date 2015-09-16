#!/usr/bin/env python

import os
import time
import sys

import config
import here
# sudo pip install -U python-digitalocean
import digitalocean as do
import update
import util


def launch_cloudmaster():
    _, _, do_token = util.read_do_credential()
    mgr = do.Manager(token=do_token)
    delay = 2
    class Done:
        pass
    for d in mgr.get_all_droplets():
        if d.name == config.cloudmaster_name:
            if raw_input("Found an existing cloudmaster;"
                    + " should I kill it? (y/N): ") != 'y':
                print "OK, bye."
                sys.exit(0)
            print "Killing..."
            ip_ = d.ip_address
            d.destroy()
            util.wait_droplet(d)
            print "Removing from known_hosts..."
            os.system('ssh-keygen -f "%s/.ssh/known_hosts" -R %s'
                      % (os.path.expanduser("~"),
                         ip_))
            print "Digitan Ocean doesn't like us immediately creating"
            print "instances with the same name as one we just killed."
            print "Waiting for 20 seconds to be on the safe side..."
            time.sleep(20)
    print "Ordering the creation of the droplet..."
    droplet = do.Droplet(token=do_token,
                         name=config.cloudmaster_name,
                         region='sgp1',
                         image='ubuntu-14-04-x64',
                         size='1gb',
                         ssh_keys=[97623],  # cloudmaster key
                         backups=False)
    droplet.create()
    print "Waiting for instance to run..."
    util.wait_droplet(droplet)
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
    print "Copying bootstrap file..."
    os.system("scp -i %s %s root@%s:"
              % (config.key_path,
                 here.bootstrap_path,
                 util.get_cloudmaster_address()))
    print "Bootstrapping..."
    util.ssh_cloudmaster("sudo SALT_VERSION=%s ./bootstrap.bash"
                            % config.salt_version,
                         ".log")
    print
    print "Done launching."
    update.print_errors()

def init_dir(path):
    return util.ssh_cloudmaster("sudo mkdir %s" % path)


if __name__ == '__main__':
    launch_cloudmaster()
