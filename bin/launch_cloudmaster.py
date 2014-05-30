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
    do_id, do_api_key = util.read_do_credential()
    mgr = do.Manager(client_id=do_id, api_key=do_api_key)
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
            d.destroy(scrub_data=False)
            try:
                while True:
                    events = d.get_events()
                    for event in events:
                        event.load()
                        if event.percentage is not None:
                            print "%s%%..." % event.percentage
                            if event.percentage == u"100":
                               raise Done
                    time.sleep(delay)
            except Done:
                pass
            print "Removing from known_hosts..."
            os.system('ssh-keygen -f "%s/.ssh/known_hosts" -R %s'
                      % (os.path.expanduser("~"),
                         ip_))
    print "Ordering the creation of the droplet..."
    droplet = do.Droplet(client_id=do_id,
                         api_key=do_api_key,
                         name=config.cloudmaster_name,
                         region_id=4,  # New York 2
                         image_id=3101045,  # Ubuntu 12.04.4 x64
                         size_id=63,  # 1GB
                         ssh_key_ids=[97623],  # cloudmaster key
                         backup_active=False)
    droplet.create()
    print "Waiting for instance to run..."
    try:
        while True:
            events = droplet.get_events()
            for event in events:
                event.load()
                if event.percentage is not None:
                    print "%s%%..." % event.percentage
                    if event.percentage == u"100":
                        raise Done
            time.sleep(delay)
    except Done:
        pass
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
