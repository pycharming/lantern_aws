import os
import re
import stat
import sys
import time
from functools import wraps

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
def get_address():
    """
    Return the address of the 'cloudmaster' machine in the current region.
    """
    import region
    name = config.cloudmaster_name
    try:
        reservation, = region.connect().get_all_instances(
                filters={'tag:Name': name})
        instance, = reservation.instances
        if instance.ip_address is None:
            raise RuntimeError("'%s' looks like a dead instance." % name)
        return instance.ip_address
    except ValueError:
        # `s` is neither an IP nor an EC2 name.  It may still be
        # something that can be resolved to an IP.  Let's try.
        raise RuntimeError(("'%s' not found in current region."
                            + "  Are you sure you launched it?") % name)

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
    full_cmd = "ssh -o StrictHostKeyChecking=no -i %s ubuntu@%s" % (
                    config.key_path,
                    get_address())
    if cmd:
        full_cmd += " '%s'" % cmd
    if out:
        full_cmd += "| tee %s" % out
    return os.system(full_cmd)
