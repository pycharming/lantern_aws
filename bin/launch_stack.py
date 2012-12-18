#!/usr/bin/env python

# Watch for DRY (Don't Repeat Yourself) violation warnings.  If you change
# these values, make sure to update unpack_template.py accordingly.

import base64
import os
import random
from cStringIO import StringIO
import sys
import tarfile
import tempfile
import zlib

import boto

from bin_dir import bin_dir


def run(node_type, stack_name, conn=None):
    here = bin_dir()

    sio = StringIO()

    # DRY warning: mode.
    with tarfile.open(fileobj=sio, mode='w:bz2', dereference=True) as tf:

        #DRY warning: bootstrap directory name.
        tf.add(os.path.join(here, '..', 'bootstrap'),
               arcname='bootstrap')

    blob = sio.getvalue()
    sanitized_blob = base64.b64encode(blob)

    template = file(os.path.join(here, 'unpack_template.py')).read()

    # DRY warning: placeholder string.
    self_extractable = template.replace("<PUT_BLOB_HERE>", sanitized_blob)

    b64_se = base64.b64encode(self_extractable)


    # The blob is broken into parts because each cloudformation template parameter
    # has a size limit.  This blob is reassembled inside the template to become
    # the user-data.
    sizelimit = 4096
    parts = [b64_se[i*sizelimit:(i+1)*sizelimit]
             for i in xrange(4)]

    parameters = zip(["Bootstrap", "Bootstrap2", "Bootstrap3", "Bootstrap4"],
                     # Omit empty parts.
                     filter(None, parts))

    if node_type == 'lantern-peer':
        ssl_proxy_port = random.randint(1024, 61024)
        parameters.append(("LanternSSLProxyPort", ssl_proxy_port))

    template = file(os.path.join(here,
                                 '..',
                                 'cloudformation',
                                 node_type + '.json')).read()

    conn = conn or boto.connect_cloudformation()
    return conn.create_stack(stack_name,
                             template_body=template,
                             parameters=parameters)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Launch a new node."
        print "Usage: %s <node-type> <node-name>" % sys.argv[0]
        print "Valid node types are:"
        for filename in os.listdir(os.path.join(bin_dir(),
                                                '..',
                                                'cloudformation')):
            if filename.endswith('.json'):
                print "   ", filename[:-len('.json')]
        sys.exit(1)
    print run(*sys.argv[1:])
