#!/usr/bin/env python

import os
import subprocess
import sys


here = os.path.dirname(sys.argv[0])
out = subprocess.check_output([here + "/ssh_cloudmaster.py",
                              "'sudo salt \"fp-*\" test.ping | wc -l'"])
print "Got", int(out.strip().split()[0]) // 2, "fallbacks."
