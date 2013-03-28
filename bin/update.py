#!/usr/bin/env python

import os

import util


def update(key_path, address):
    print "Pushing salt config..."
    util.rsync(key_path, address)
    os.system(("ssh -i %s ubuntu@%s 'sudo salt-call state.highstate'"
               + " | tee .log") % (key_path, address))
    print
    print "Done updating. The following look like errors:"
    print
    os.system("grep -i error .log")
    os.system("grep False .log")

if __name__ == '__main__':
    util.call_with_key_path_and_address(update)
