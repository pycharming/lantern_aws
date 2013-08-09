#!/usr/bin/env python

import os

import config
import here
import region
import util


def update():
    util.set_secret_permissions()
    print "Uploading minion config..."
    upload_cloudmaster_minion_config()
    print "Uploading pillars..."
    upload_pillars()
    print "Uploading states..."
    rsync_salt()

def apply_update():
    util.ssh_cloudmaster("sudo salt-call state.highstate", ".log")
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
error = os.system("FALLBACK_SERVER_HOST=%s FALLBACK_SERVER_PORT=%s %s/build-installers.bash"
assert not error
"""
    known_false_positives = set(filter(None,
                                       map(str.strip,
                                           raw_false_positives.split("\n"))))
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
                      % (config.key_path,
                         src,
                         util.get_address(),
                         dst))
    if not error:
        print "Rsynced successfuly."
    return error

def upload_cloudmaster_minion_config():
    address = util.get_address()
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
                          + r""" ) > /home/ubuntu/minion""")
                         % (aws_id,
                            aws_key,
                            config.aws_region,
                            region.get_ami(),
                            do_id,
                            do_key,
                            config.do_region,
                            config.controller))
    util.ssh_cloudmaster('sudo mv /home/ubuntu/minion /etc/salt/minion'
                         ' && sudo chown root:root /etc/salt/minion'
                         ' && sudo chmod 600 /etc/salt/minion')

def upload_pillars():
    refr_tok = file(os.path.join(here.secrets_path,
                                 'lantern_aws',
                                 'lanterndonors.refresh_token')).read().strip()
    util.ssh_cloudmaster((
            'echo "lanterndonors_refrtok: %s" > cloudmaster.sls '
            ' && echo "salt_version: %s" > salt.sls '
            # Hack so every instance will read specific pillars from a file named
            # with the <instance_name>.sls scheme.
            r' && echo "include: [{{ grains[\"id\"] }}]" > fallback_proxy.sls '
            r' && echo "base: {\"*\": [salt], '
                             r'\"cloudmaster\": [cloudmaster], '
                             r'\"fp-*\": [fallback_proxy]}" '
                ' > top.sls '
            ' && sudo mv salt.sls top.sls cloudmaster.sls fallback_proxy.sls '
                ' /srv/pillar/ '
            ' && sudo chown -R root:root /srv/pillar '
            ' && sudo chmod -R 600 /srv/pillar '
            ) % (refr_tok, config.salt_version))

if __name__ == '__main__':
    update()
