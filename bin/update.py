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

EXPECTED_PRODUCTION_GIT_LFS_STATUS_OUTPUT = normalize_status_output("""\
On branch master
Git LFS objects to be pushed to origin/master:
Git LFS objects to be committed:
Git LFS objects not staged for commit:
""")

def check_master_if_in_production():
    if util.in_production():
        status_output = normalize_status_output(
                subprocess.check_output(['git', 'status']))
        if status_output != EXPECTED_PRODUCTION_GIT_STATUS_OUTPUT:
            not_up_to_date()
        pull_output = subprocess.check_output(['git', 'pull'])
        if pull_output != EXPECTED_PRODUCTION_GIT_PULL_OUTPUT:
            not_up_to_date()
        lfs_status_output = normalize_status_output(
                subprocess.check_output(['git', 'lfs', 'status']))
        if lfs_status_output != EXPECTED_PRODUCTION_GIT_LFS_STATUS_OUTPUT:
            not_up_to_date()

def not_up_to_date():
    print
    print "*** UP-TO-DATE MASTER CHECKOUT REQUIRED ***"
    print
    print "Sorry, you can only deploy to the production cloudmaster"
    print "from an up-to-date master checkout with git-lfs installed."
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
                         ('root@' if as_root else 'lantern@'),
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
    if not util.in_dev() and not util.in_staging() and not util.in_production():
        assert util.in_production(), "Environment unknown!"

    _, _, do_token = util.read_do_credential()
    vultr_apikey = util.read_vultr_credential()
    linode_password, linode_apikey, linode_tokyo_apikey = util.read_linode_credential()
    cfgsrv_token, cfgsrv_redis_url, cfgsrv_redis_test_pass \
        = util.read_cfgsrv_credential()
    github_token = util.read_github_token()
    loggly_token = util.read_loggly_token()
    if util.in_production():
        slack_webhook_url = util.read_slack_webhook_url()
    else:
        slack_webhook_url = util.read_slack_staging_webhook_url()

    environment = "production"

    if util.in_staging():
        environment = "staging"
        cfgsrv_redis_url = "rediss://:testing@redis-staging.getlantern.org:6380"

    redis_host = cfgsrv_redis_url.split('@')[1]
    redis_domain = redis_host.split(":")[0]
    redis_via_stunnel_url = cfgsrv_redis_url.split('@')[0].replace("rediss", "redis") + "@localhost:6380"

    if util.in_dev():
        environment = "dev"
        redis_host = "%s:6379" % config.cloudmaster_address
        cfgsrv_redis_url = "redis://redis:%s@%s" % (cfgsrv_redis_test_pass, redis_host)
        redis_domain = "redis-staging.getlantern.org"
        # Bypass stunnel in dev environments because we're not encrypting connections to Redis
        redis_via_stunnel_url = cfgsrv_redis_url

    util.ssh_cloudmaster((
            'echo "salt_version: %s" > salt.sls '
            # Hack so every instance will read specific pillars from a file
            # named with the <instance_name>.sls scheme.
            r' && echo "include: [{{ grains[\"id\"] }}]" >> salt.sls '
            ' && echo "" > $(hostname).sls""'
            ' && echo "environment: %s" > global.sls '
            ' && echo "in_dev: %s" >> global.sls '
            ' && echo "in_staging: %s" >> global.sls '
            ' && echo "in_production: %s" >> global.sls '
            ' && echo "datacenter: %s" >> global.sls '
            ' && echo "cfgsrv_redis_url: %s" >> global.sls'
            ' && echo "redis_via_stunnel_url: %s" >> global.sls'
            ' && echo "redis_host: %s" >> global.sls'
            ' && echo "redis_domain: %s" >> global.sls'
            ' && echo "slack_webhook_url: %s" >> global.sls '
            ' && echo "cloudmaster_name: %s" >> global.sls '
            ' && echo "do_token: %s" > do_credential.sls'
            ' && echo "vultr_apikey: %s" > vultr_credential.sls'
            ' && echo "linode_password: \'%s\'" > linode_credential.sls '
            ' && echo "linode_apikey: %s" >> linode_credential.sls '
            ' && echo "linode_tokyo_apikey: %s" >> linode_credential.sls '
            ' && echo "cfgsrv_token: %s" > cfgsrv_credential.sls'
            ' && echo "cfgsrv_redis_test_pass: \"%s\"" >> cfgsrv_credential.sls'
            ' && echo "github_token: %s" > github_token.sls'
            ' && echo "loggly_token: %s" > loggly_token.sls'
            r' && echo "base: {\"fp-*\": [cfgsrv_credential, vultr_credential, github_token, loggly_token], \"cm-*\": [do_credential, vultr_credential, linode_credential, cfgsrv_credential], \"cs-*\": [cfgsrv_credential], \"*\": [global, salt]}" > top.sls '
            ' && sudo mv salt.sls global.sls top.sls do_credential.sls vultr_credential.sls linode_credential.sls cfgsrv_credential.sls github_token.sls loggly_token.sls $(hostname).sls /srv/pillar/ '
            ' && sudo chown -R root:root /srv/pillar '
            ' && sudo chmod -R 600 /srv/pillar '
            ) % (config.salt_version,
                 environment,
                 util.in_dev(),
                 util.in_staging(),
                 util.in_production(),
                 config.datacenter,
                 cfgsrv_redis_url,
                 redis_via_stunnel_url,
                 redis_host,
                 redis_domain,
                 slack_webhook_url,
                 config.cloudmaster_name,
                 do_token,
                 vultr_apikey,
                 linode_password,
                 linode_apikey,
                 linode_tokyo_apikey,
                 cfgsrv_token,
                 cfgsrv_redis_test_pass,
                 github_token,
                 loggly_token),
            as_root=as_root)

if __name__ == '__main__':
    check_master_if_in_production()
    update('--as-root' in sys.argv)
