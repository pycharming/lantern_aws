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
    do_id, do_api_key = read_do_credential()
    mgr = do.Manager(client_id=do_id, api_key=do_api_key)
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
    d = yaml.load(file(os.path.join(here.secrets_path,
                                    'lantern_aws',
                                    'do_credential')))
    return d['client_id'], d['api_key']

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
