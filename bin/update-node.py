#!/usr/bin/env python

import os
import shutil
import sys
import tempfile


if not (2 <= len(sys.argv) <= 3):
    print "Usage: %s <instance address> [<branch>]" % sys.argv[0]
    sys.exit(1)

here = os.path.dirname(sys.argv[0])

address = sys.argv[1]
if len(sys.argv) > 2:
    branch = sys.argv[2]
else:
    branch = 'lantern-peer'

print "Pushing to", address, "..."
repo_root = os.path.join(here, '..')
os.chdir(repo_root)
if os.system("git push -f gitpuppet@%s:configure %s:master"
             % (address, branch)):
    print "Something went wrong."
else:
    print "Done."
