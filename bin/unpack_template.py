#!/usr/bin/env python

# Watch for DRY (Don't Repeat Yourself) violation warnings.  If you change
# these values, make sure to update launch_lantern_instance.py accordingly.

import base64
import os
from StringIO import StringIO
import sys
import tarfile
import tempfile


assert __name__ == '__main__', "Don't import me, call me as a script."

here = os.path.dirname(sys.argv[0])

# DRY warning: placeholder string.
sio = StringIO(base64.b64decode("<PUT_BLOB_HERE>"))

tmpdir = tempfile.mkdtemp(prefix='lantern-bootstrap')

# DRY warning: mode.
with tarfile.open(fileobj=sio, mode='r:bz2') as tf:
    tf.extractall(tmpdir)

# DRY warning: bootstrap directory name.
os.system(os.path.join(tmpdir, 'bootstrap', 'run'))
