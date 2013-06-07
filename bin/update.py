#!/usr/bin/env python

import os

import config
import here
import region
import util


def update():
    util.set_secret_permissions()
    print "Pushing salt config..."
    rsync_salt()
    os.system(("ssh -i %s ubuntu@%s 'sudo salt-call state.highstate'"
               + " | tee .log") % (region.get_key_path(), util.get_address()))
    print
    print "Done updating."
    print_errors()

def print_errors():
    raw_false_positives = """
-// Set this value to "true" to get emails only on errors. Default
-//Unattended-Upgrade::MailOnlyOnError "true";
-# One of 'garbage', 'trace', 'debug', info', 'warning', 'error', 'critical'.
-# Default: 'False'
-#delete_sshkeys: False
liberror-perl changed from absent to 0.17-1
Changes:   liberror-perl: { new : 0.17-1
"""
    known_false_positives = filter(None,
                                   map(str.strip,
                                       raw_false_positives.split("\n")))
    print
    print "Any prints below may be caused by errors:"
    print
    for line in file(".log"):
        line = line.strip()
        if (line not in known_false_positives
            and ("error" in line.lower()
                 or "False" in line)):
            print line

def upload_secrets():
    return rsync(os.path.join(here.secrets_path, 'build-installers'),
                 '/home/lantern/secure')
def rsync_salt():
    return rsync(here.salt_states_path, '/srv/salt')

def rsync(src, dst):
    error = os.system(("rsync -e 'ssh -o StrictHostKeyChecking=no -i %s'"
                       + " -azLk %s/ ubuntu@%s:%s")
                      % (region.get_key_path(),
                         src,
                         util.get_address(),
                         dst))
    if not error:
        print "Rsynced successfuly."
    return error


if __name__ == '__main__':
    update()
