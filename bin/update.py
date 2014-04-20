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
        print "Rsynced successfully."
    return error

def upload_cloudmaster_minion_config():
    address = util.get_address()
    do_id, do_key = util.read_do_credential()
    util.ssh_cloudmaster((r"""(echo "master: salt" """
                          + r""" && echo "grains:" """
                          + r""" && echo "    aws_region: %s " """
                          + r""" && echo "    aws_ami: %s " """
                          + r""" && echo "    do_id: %s " """
                          + r""" && echo "    do_key: %s " """
                          + r""" && echo "    do_region: %s " """
                          + r""" && echo "    controller: %s " """
                          + r""" && echo "    production_controller: %s " """
                          + r""" ) > /home/ubuntu/minion""")
                         % (config.aws_region,
                            region.get_ami(),
                            do_id,
                            do_key,
                            config.do_region,
                            config.controller,
                            'lanternctrl1-2'))
    util.ssh_cloudmaster('sudo mv /home/ubuntu/minion /etc/salt/minion'
                         ' && sudo chown root:root /etc/salt/minion'
                         ' && sudo chmod 600 /etc/salt/minion')

def upload_pillars():
    aws_id, aws_key = util.read_aws_credential()
    util.ssh_cloudmaster((
            'echo "branch: check-all-fallbacks" > cloudmaster.sls '
            ' && echo "salt_version: %s" > salt.sls '
            ' && echo "aws_id: %s"  > aws_credential.sls'
            ' && echo "aws_key: %s" >> aws_credential.sls'
            # Hack so every instance will read specific pillars from a file named
            # with the <instance_name>.sls scheme.
            r' && echo "include: [{{ grains[\"id\"] }}]" > fallback_proxy.sls '
            r' && echo "installer_bucket: %s" >> fallback_proxy.sls '
            r' && echo "installer_filename: %s" >> fallback_proxy.sls '
            r' && echo "base: {\"*\": [salt, aws_credential], '
                             r'\"cloudmaster\": [cloudmaster], '
                             r'\"fp-*\": [fallback_proxy]}" '
                ' > top.sls '
            ' && sudo mv salt.sls top.sls cloudmaster.sls fallback_proxy.sls '
                ' aws_credential.sls /srv/pillar/ '
            ' && sudo chown -R root:root /srv/pillar '
            ' && sudo chmod -R 600 /srv/pillar '
            ) % (config.salt_version,
                 aws_id,
                 aws_key,
                 config.installer_bucket,
                 config.installer_filename))

if __name__ == '__main__':
    update()
