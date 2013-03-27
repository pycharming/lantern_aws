#!/usr/bin/env python

import re
import os
import sys

import here
import region
import util


def update(machine):
    if re.match(r'\d+\.\d+\.\d+\.\d+', machine):
        address = machine
    else:
        conn = region.connect()
        try:
            reservation, = conn.get_all_instances(
                    filters={'tag:Name': machine})
            instance, = reservation.instances
            address = instance.ip_address
            if address is None:
                print machine, "looks like a dead instance."
                sys.exit(1)
        except ValueError:
            # `machine` is neither an IP nor an EC2 name.  It may still be
            # something that can be resolved to an IP.  Let's try.
            address = machine
    _, key_path = region.get_key()
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
    machine = (len(sys.argv) == 2 and sys.argv[1]
               or os.environ.get('MACHINETOUPDATE'))
    if machine:
        update(machine)
    else:
        print >> sys.stderr, (
"""Usage: %s <ip or name of machine to update>
(You may also set that in the MACHINETOUPDATE environment variable.)"""
                % sys.argv[0])
        sys.exit(1)
