import os
import re
import stat
import sys
import time
from functools import wraps

import digitalocean as do
import yaml

import config
import here



def memoized(f):
    d = {}
    @wraps(f)
    def deco(*args):
        try:
            return d[args]
        except KeyError:
            ret = d[args] = f(*args)
            return ret
    return deco

@memoized
def get_cloudmaster_address():
    """
    Return the address of the currently configured cloudmaster.
    """
    name = config.cloudmaster_name
    env_key = '%s_IP' % name.replace('-', '_')
    ip_ = os.environ.get(env_key)
    if ip_ is not None:
        return ip_
    _, _, do_token = read_do_credential()
    mgr = do.Manager(token=do_token)
    for instance in mgr.get_all_droplets():
        if instance.name == name:
            ret = instance.ip_address
            print "WARNING: set the following in your .bashrc for faster"
            print "execution next time:"
            print
            print "    export %s=%s" % (env_key, ret)
            return ret

@memoized
def read_aws_credential():
    id_, key = None, None
    for line in file(config.aws_credential_path):
        line = line.strip()
        m = re.match(r"AWSAccessKeyId=(.*)", line)
        if m:
            id_ = m.groups()[0]
        m = re.match("AWSSecretKey=(.*)", line)
        if m:
            key = m.groups()[0]
    assert id_ and key
    return id_, key

@memoized
def read_do_credential():
    return secrets_from_yaml(['lantern_aws', 'do_credential'],
                             ['client_id', 'api_key', 'rw_token'])

@memoized
def read_cf_credential():
    return secrets_from_yaml(['cloudflare.txt'],
                             ['user', 'api_key'])

def read_azure_ssh_pass():
    return secrets_from_yaml(['lantern_aws', 'azure.yaml'],
                             ['ssh_pass'])[0]

def secrets_from_yaml(path, keys):
    d = yaml.load(file(os.path.join(here.secrets_path, *path)))
    return map(d.get, keys)

def set_secret_permissions():
    """Secret files should be only readable by user, but git won't remember
    read/write settings for group and others.

    We can't even create an instance unless we restrict the permissions of the
    corresponding .pem.
    """
    for path, dirnames, filenames in os.walk(here.secrets_path):
        for name in filenames:
            os.chmod(os.path.join(path, name), stat.S_IREAD)

def ssh_cloudmaster(cmd=None, out=None):
    import region
    full_cmd = "ssh -o StrictHostKeyChecking=no -i %s root@%s" % (
                    config.key_path,
                    get_cloudmaster_address())
    if cmd:
        full_cmd += " '%s'" % cmd
    if out:
        full_cmd += "| tee %s" % out
    return os.system(full_cmd)

def wait_droplet(d):
    """
    Wait for the completion of a command on a Digital Ocean droplet.
    """
    delay = 2
    while True:
        actions = d.get_actions()
        if actions:
            last_action = actions[-1]
            last_action.load()
            if last_action.status == 'completed':
                return
            else:
                print "status: %s ..." % last_action.status
        time.sleep(delay)
