#!/usr/bin/env python

import os
import subprocess
import sys

import config
import here
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
    if util.in_production():
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

def update(as_root=False):
    util.set_secret_permissions()
    print "Uploading master config..."
    upload_master_config(as_root)
    print "Uploading pillars..."
    upload_pillars(as_root)
    print "Uploading states..."
    rsync_salt(as_root)

def rsync_salt(as_root):
    return rsync(here.salt_states_path, '/srv/salt', as_root)

def scp(src, dst, as_root=False):
    error = os.system("scp -o StrictHostKeyChecking=no %s %s%s:%s"
                      % (src,
                         ('root@' if as_root else ''),
                         config.cloudmaster_address,
                         dst))
    if not error:
        print "scp'd successfully."
    return error

def rsync(src, dst, as_root=False):
    error = os.system(("rsync -e 'ssh -o StrictHostKeyChecking=no'"
                       + ("" if as_root else " --rsync-path='sudo rsync' ") # we set --rsync-path to use sudo so that we can overwrite files owned by root
                       + " -azLk %s/ %s%s:%s")
                      % (src,
                         ('root@' if as_root else ''),
                         config.cloudmaster_address,
                         dst))
    if not error:
        print "Rsynced successfully."
    return error

def upload_master_config(as_root=False):
    util.ssh_cloudmaster(r"""(echo "timeout: 20" """
                         + r""" && echo "keep_jobs: 2" """
                         + r""" && echo "worker_threads: 20" """
                         + r""" ) > master""",
                         as_root=as_root)
    move_root_file('master', '/etc/salt/master', as_root)

def move_root_file(src, dst, as_root=False):
    return util.ssh_cloudmaster(('sudo mv %s %s'
                                 ' && sudo chown root:root %s'
                                 ' && sudo chmod 600 %s') % (src, dst, dst, dst),
                                as_root=as_root)

def upload_pillars(as_root=False):
    _, _, do_token = util.read_do_credential()
    vultr_apikey = util.read_vultr_credential()
    cfgsrv_token, cfgsrv_redis_url, cfgsrv_redis_test_pass \
        = util.read_cfgsrv_credential()
    secondary_redis_url = util.read_secondary_redis_credential()
    github_token = util.read_github_token()
    loggly_token = util.read_loggly_token()
    if util.in_production():
        slack_webhook_url = util.read_slack_webhook_url()
    else:
        slack_webhook_url = util.read_slack_staging_webhook_url()
    if not util.in_production():
        if util.in_staging():
            # Exception: make the staging cloudmasters use the redis instance
            # of the staging cloudmaster in Amsterdam, to be more like the
            # production setup.
            redis_address = '188.166.55.168'
        else:
            redis_address = config.cloudmaster_address
        cfgsrv_redis_url = "redis://redis:%s@%s:6379" % (cfgsrv_redis_test_pass,
                                                         redis_address)
    util.ssh_cloudmaster((
            'echo "salt_version: %s" > salt.sls '
            # Hack so every instance will read specific pillars from a file
            # named with the <instance_name>.sls scheme.
            r' && echo "include: [{{ grains[\"id\"] }}]" >> salt.sls '
            ' && echo "" > $(hostname).sls""'
            ' && echo "in_staging: %s" > global.sls '
            ' && echo "in_production: %s" >> global.sls '
            ' && echo "datacenter: %s" >> global.sls '
            ' && echo "slack_webhook_url: %s" >> global.sls '
            ' && echo "cloudmaster_name: %s" >> global.sls '
            ' && echo "do_token: %s" > do_credential.sls'
            ' && echo "vultr_apikey: %s" > vultr_credential.sls'
            ' && echo "cfgsrv_token: %s" > cfgsrv_credential.sls'
            ' && echo "cfgsrv_redis_url: %s" >> cfgsrv_credential.sls'
            ' && echo "cfgsrv_redis_test_pass: \"%s\"" >> cfgsrv_credential.sls'
            ' && echo "secondary_redis_url: \"%s\"" >> secondary_redis_credential.sls'
            ' && echo "github_token: %s" > github_token.sls'
            ' && echo "loggly_token: %s" > loggly_token.sls'
            r' && echo "base: {\"*\": [salt, global], \"fp-*\": [cfgsrv_credential, vultr_credential, secondary_redis_credential, github_token, loggly_token], \"cm-*\": [do_credential, vultr_credential, cfgsrv_credential], \"cs-*\": [cfgsrv_credential]}" > top.sls '
            ' && sudo mv salt.sls global.sls top.sls do_credential.sls vultr_credential.sls cfgsrv_credential.sls secondary_redis_credential.sls github_token.sls loggly_token.sls $(hostname).sls /srv/pillar/ '
            ' && sudo chown -R root:root /srv/pillar '
            ' && sudo chmod -R 600 /srv/pillar '
            ) % (config.salt_version,
                 util.in_staging(),
                 util.in_production(),
                 config.datacenter,
                 slack_webhook_url,
                 config.cloudmaster_name,
                 do_token,
                 vultr_apikey,
                 cfgsrv_token,
                 cfgsrv_redis_url,
                 cfgsrv_redis_test_pass,
                 secondary_redis_url,
                 github_token,
                 loggly_token),
            as_root=as_root)

if __name__ == '__main__':
    check_master_if_in_production()
    update('--as-root' in sys.argv)
