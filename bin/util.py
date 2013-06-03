import os
import re
import stat
import sys
import time

import here
import region


def get_address(s):
    if re.match(r'\d+\.\d+\.\d+\.\d+', s):
        return s
    else:
        conn = region.connect()
        try:
            reservation, = conn.get_all_instances(
                    filters={'tag:Name': s})
            instance, = reservation.instances
            if instance.ip_address is None:
                raise RuntimeError("%s looks like a dead instance." % s)
            return instance.ip_address
        except ValueError:
            # `s` is neither an IP nor an EC2 name.  It may still be
            # something that can be resolved to an IP.  Let's try.
            return s

def rsync(key_path,
          ip,
          local_path=here.salt_states_path,
          remote_path='/srv/salt'):
    error = os.system(("rsync -e 'ssh -o StrictHostKeyChecking=no -i %s'"
                       + " -azLk %s/ ubuntu@%s:%s")
                      % (key_path, local_path, ip, remote_path))
    if not error:
        print "Rsynced successfuly."
    return error

def call_with_key_path_and_address(callback):
    machine = (len(sys.argv) == 2 and sys.argv[1]
               or os.environ.get('MACHINETOUPDATE'))
    if machine:
        _, key_path = region.get_key()
        callback(key_path, get_address(machine))
    else:
        print >> sys.stderr, (
"""Usage: %s <ip or name of machine to update>
(You may also set that in the MACHINETOUPDATE environment variable.)"""
                % sys.argv[0])
        sys.exit(1)

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
