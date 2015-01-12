#!/usr/bin/env python

import os
import subprocess
import sys

import config
import here
import region
import util

def normalize_status_output(s):
    return filter(None, map(str.strip, s.split("\n")))

EXPECTED_PRODUCTION_GIT_STATUS_OUTPUT = normalize_status_output("""\
On branch master
Your branch is up-to-date with 'origin/master'.
nothing to commit, working directory clean
""")

EXPECTED_PRODUCTION_GIT_PULL_OUTPUT = "Already up-to-date.\n"

def check_master_if_in_production():
    if config.controller == config.production_controller:
        status_output = normalize_status_output(
                subprocess.check_output(['git', 'status']))
        if status_output != EXPECTED_PRODUCTION_GIT_STATUS_OUTPUT:
            not_up_to_date()
        pull_output = subprocess.check_output(['git', 'pull'])
        if pull_output != EXPECTED_PRODUCTION_GIT_PULL_OUTPUT:
            not_up_to_date()

def not_up_to_date():
    print
    print "*** UP-TO-DATE MASTER CHECKOUT REQUIRED ***"
    print
    print "Sorry, you can only deploy to the production cloudmaster"
    print "from an up-to-date master checkout."
    print
    print "If you're pretty sure that is the case, you may want to"
    print "either update git or fix `check_master_if_in_production`"
    print "in bin/update.py"
    print
    sys.exit(1)

def update():
    util.set_secret_permissions()
    print "Uploading secrets..."
    upload_secrets()
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
    error = scp(os.path.join(here.secrets_path, 'lantern_aws', 'azure.pem'),
                '/root/')
    if error:
        return error
    return move_root_file('/root/azure.pem', '/etc/salt/azure.pem')

def rsync_salt():
    return rsync(here.salt_states_path, '/srv/salt')

def scp(src, dst):
    error = os.system("scp -o StrictHostKeyChecking=no -i %s %s root@%s:%s"
                      % (config.key_path,
                         src,
                         util.get_cloudmaster_address(),
                         dst))
    if not error:
        print "scp'd successfully."
    return error

def rsync(src, dst):
    error = os.system(("rsync -e 'ssh -o StrictHostKeyChecking=no -i %s'"
                       + " -azLk %s/ root@%s:%s")
                      % (config.key_path,
                         src,
                         util.get_cloudmaster_address(),
                         dst))
    if not error:
        print "Rsynced successfully."
    return error

def upload_cloudmaster_minion_config():
    address = util.get_cloudmaster_address()
    do_id, do_key, _ = util.read_do_credential()
    util.ssh_cloudmaster((r"""(echo "master: salt" """
                          + r""" && echo "grains:" """
                          + r""" && echo "    aws_region: %s " """
                          + r""" && echo "    aws_ami: %s " """
                          + r""" && echo "    do_id: %s " """
                          + r""" && echo "    do_key: %s " """
                          + r""" && echo "    do_region: %s " """
                          + r""" && echo "    controller: %s " """
                          + r""" && echo "    production_controller: %s " """
                          + r""" ) > /root/minion""")
                         % (config.aws_region,
                            region.get_ami(),
                            do_id,
                            do_key,
                            config.do_region,
                            config.controller,
                            config.production_controller))
    move_root_file('/root/minion', '/etc/salt/minion')

def move_root_file(src, dst):
    return util.ssh_cloudmaster(('sudo mv %s %s'
                                 ' && sudo chown root:root %s'
                                 ' && sudo chmod 600 %s') % (src, dst, dst, dst))

def upload_pillars():
    aws_id, aws_key = util.read_aws_credential()
    cf_id, cf_key = util.read_cf_credential()
    azure_ssh_pass = util.read_azure_ssh_pass()
    util.ssh_cloudmaster((
            'echo "branch: check-all-fallbacks" > cloudmaster.sls '
            ' && echo "private_networking: %s" >> cloudmaster.sls '
            ' && echo "default_profile: %s" >> cloudmaster.sls '
            ' && echo "azure_ssh_pass: %s" >> cloudmaster.sls '
            ' && echo "salt_version: %s" > salt.sls '
            # Hack so every instance will read specific pillars from a file
            # named with the <instance_name>.sls scheme.
            r' && echo "include: [{{ grains[\"id\"] }}]" >> salt.sls '
            ' && echo "aws_id: %s"  > aws_credential.sls'
            ' && echo "aws_key: %s" >> aws_credential.sls'
            ' && echo "cf_id: %s"  > cf_credential.sls'
            ' && echo "cf_key: %s" >> cf_credential.sls'
            r' && echo "base: {\"*\": [salt, aws_credential], \"fl-*\": [cf_credential]}" > top.sls '
            ' && sudo mv salt.sls top.sls cloudmaster.sls aws_credential.sls cf_credential.sls /srv/pillar/ '
            ' && sudo chown -R root:root /srv/pillar '
            ' && sudo chmod -R 600 /srv/pillar '
            ) % (config.private_networking,
                 config.default_profile,
                 azure_ssh_pass,
                 config.salt_version,
                 aws_id,
                 aws_key,
                 cf_id,
                 cf_key))

if __name__ == '__main__':
    check_master_if_in_production()
    update()
