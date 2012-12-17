#!/usr/bin/env python

import logging
import os
import sys

from bin_dir import bin_dir


def run(node_type, address):
    here = bin_dir()
    repo_root = os.path.join(here, '..')
    os.chdir(repo_root)
    os.system("git push -f gitsalt@%s:config %s:master"
              % (address, node_type))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Usage: %s <node-type> <address>" % sys.argv[0]
        sys.exit(1)
    run(*sys.argv[1:])
