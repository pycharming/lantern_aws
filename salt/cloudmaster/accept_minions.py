#!/usr/bin/env python

from datetime import datetime
import os
import random
import string
import sys
import time


pillar_tmpl = """\
controller: lanternctrl1-2
auth_token: %s
install-from: git
instance_id: %s
proxy_protocol: tcp
"""

AUTH_TOKEN_ALPHABET = string.letters + string.digits
AUTH_TOKEN_LENGTH = 64


def random_auth_token():
    return ''.join(random.choice(AUTH_TOKEN_ALPHABET)
                   for _ in xrange(AUTH_TOKEN_LENGTH))

def minion_id(prefix, n):
    return '%s-jp-%s-%s' % (
        prefix,
        datetime.now().date().isoformat().replace('-', ''),
        str(n).zfill(3))

def accept_minions(prefix, start, number):
    for i in xrange(start, start+number):
        id_ = minion_id(prefix, i)
        file("/srv/pillar/%s.sls" % id_, 'w').write(
            pillar_tmpl % (random_auth_token(), id_))
        os.system("salt-key -ya %s" % id_)
        time.sleep(10)
        os.system("salt %s state.highstate | tee hslog" % id_)


if __name__ == '__main__':
    accept_minions(sys.argv[1],
                   int(sys.argv[2]),
                   int(sys.argv[3]))
