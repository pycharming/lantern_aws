import os
import stat

import yaml

import config
import here
from misc_util import memoized, whitelist_ssh


def in_production():
    return config.cloudmaster_name in config.production_cloudmasters

def in_staging():
    return config.cloudmaster_name.endswith('staging')

@memoized
def read_do_credential():
    return secrets_from_yaml(['lantern_aws', 'do_credential'],
                             ['client_id', 'api_key', 'rw_token'])

@memoized
def read_vultr_credential():
    return secrets_from_yaml(['vultr.md'],
                             ['api-key'])[0]

@memoized
def read_cfgsrv_credential():
    return secrets_from_yaml(['lantern_aws', 'config_server.yaml'],
                             ['auth_token', 'redis_url', 'redis_test_pass'])

@memoized
def read_secondary_redis_credential():
    return secrets_from_yaml(['lantern_aws', 'secondary_redis.yaml'],
                             ['secondary_redis_url'])[0]

@memoized
def read_github_token():
    return secrets_from_yaml(['github.md'],
                             ['repo-token'])[0]

@memoized
def read_loggly_token():
    return secrets_from_yaml(['loggly.txt'],
                             ['bravenewsoft.loggly.com'])[0]['token']

@memoized
def read_slack_webhook_url():
    return secrets_from_yaml(['lantern_aws', 'slack.yaml'],
                             ['webhook_url'])[0]

@memoized
def read_slack_staging_webhook_url():
    return secrets_from_yaml(['lantern_aws', 'slack.yaml'],
                             ['staging_webhook_url'])[0]

def secrets_from_yaml(path, keys):
    d = yaml.load(file(os.path.join(here.secrets_path, *path)))
    return map(d.get, keys)

def set_secret_permissions():
    """Secret files should be only readable by user, but git won't remember
    read/write settings for group and others.

    We can't even create an instance unless we restrict the permissions of the
    corresponding .pem.
    """
    for path, dirnames, filenames in os.walk(os.path.join(here.secrets_path,
                                                          'lantern_aws')):
        for name in filenames:
            os.chmod(os.path.join(path, name), stat.S_IREAD)

def ssh_cloudmaster(cmd=None, out=None):
    whitelist_ssh()
    full_cmd = "ssh -o StrictHostKeyChecking=no -i %s root@%s" % (
                    config.key_path,
                    config.cloudmaster_address)
    if cmd:
        full_cmd += " '%s'" % cmd
    if out:
        full_cmd += "| tee %s" % out
    return os.system(full_cmd)
