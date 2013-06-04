import os
import re
import stat
import sys
import time
from functools import wraps

import config
import here
import region


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
    for line in file(os.path.join(here.secrets_path,
                                  'lantern_aws',
                                  'aws_credential')):
        line = line.strip()
        m = re.match(r"AWSAccessKeyId=(.*)", line)
        if m:
            id_ = m.groups()[0]
        m = re.match("AWSSecretKey=(.*)", line)
        if m:
            key = m.groups()[0]
    assert id_ and key
    return id_, key

def set_secret_permissions():
    """Secret files should be only readable by user, but git won't remember
    read/write settings for group and others.

    We can't even create an instance unless we restrict the permissions of the
    corresponding .pem.
    """
    aws_dir = os.path.join(here.secrets_path, 'lantern_aws')
    for filename in os.listdir(aws_dir):
        os.chmod(os.path.join(aws_dir, filename),
                 stat.S_IREAD)
