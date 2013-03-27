import os
import time

import here


def rsync(key_path, ip, remote_path='/srv/salt'):
    error = os.system(("rsync -e 'ssh -o StrictHostKeyChecking=no -i %s'"
                       + " -az %s/ ubuntu@%s:%s")
                      % (key_path, here.salt_states_path, ip, remote_path))
    if not error:
        print "Rsynced successfuly."
    return error
