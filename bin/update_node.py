#!/usr/bin/env python

import os
import sys

from bin_dir import bin_dir


def run(address, node_type):
    here = bin_dir()
    print "Pushing to", address, "..."
    repo_root = os.path.join(here, '..')
    os.chdir(repo_root)
    if os.system("git push -f gitsalt@%s:config %s:master"
                 % (address, node_type)):
        print "Something went wrong."
    else:
        print "Done."

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Usage: %s <instance address> <personality>" % sys.argv[0]
        sys.exit(1)
    run(*sys.argv[1:])
