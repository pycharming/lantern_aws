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
    upload_cloudmaster_minion_config()
    os.system(("ssh -i %s ubuntu@%s 'sudo salt-call state.highstate'"
               + " | tee .log") % (region.get_key_path(), util.get_address()))
    print
    print "Done updating."
    print_errors()

def print_errors():
    raw_false_positives = """
-// Set this value to "true" to get emails only on errors. Default
-//Unattended-Upgrade::MailOnlyOnError "true";
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

def rsync_salt():
    error = os.system(("rsync -e 'ssh -o StrictHostKeyChecking=no -i %s'"
                       + " -azLk %s/ ubuntu@%s:/srv/salt")
                      % (region.get_key_path(),
                         here.salt_states_path,
                         util.get_address()))
    if not error:
        print "Rsynced successfuly."
    return error

def upload_cloudmaster_minion_config():
    key_path = region.get_key_path()
    aws_id, aws_key = util.read_aws_credential()
    os.system((r"""ssh -i %s ubuntu@%s '("""
               + r"""echo "master: salt" """
               + r"""echo "grains:" """
               + r""" && echo "    aws_id: %s" """
               + r""" && echo "    aws_key: \"%s\"" """
               + r""" && echo "    aws_region: %s " """
               + r""" && echo "    aws_ami: %s ") """
               + r""" > /srv/salt/minion'""")
              % (region.get_key_path(),
                 util.get_address(),
                 aws_id,
                 aws_key,
                 config.region,
                 region.get_ami()))


if __name__ == '__main__':
    update()
