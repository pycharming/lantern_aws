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
    print "Done updating. Any prints below may be caused by errors:"
    print
    os.system("grep -i error .log")
    os.system("grep False .log")

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
