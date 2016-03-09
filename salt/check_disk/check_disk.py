#!/usr/bin/env python

import os.path
import traceback

import psutil

from alert import alert


# In percentage of disk usage.
# These may seem low, but psutil percentages are actually some 5% lower than
# those reported by `df`, so I'm being a bit conservative here.
warning_threshold = 80
critical_threshold = 90
# Files larger than this will be removed when we hit critical usage. This
# figure was chosen to keep syslog rotations that haven't exceeded their
# prescribed size (200 MB, at the time of this writing) by more than 20%.
max_size = 240 * 1024 * 1024


def delete_big_files(_, dirname, names):
    for name in names:
        path = os.path.join(dirname, name)
        if os.path.isdir(path):
            continue
        if os.path.getsize(path) > max_size:
            try:
                os.unlink(path)
            except:
                traceback.print_exc()

def run():
    usage = psutil.disk_usage('/').percent
    print "Usage: %s%%" % usage
    if usage > critical_threshold:
        print "Disk usage *critical*; clearing big files in /var/log and rebooting!"
        alert("disk-usage-critical",
              details={'usage': usage},
              text="Using %s%% of disk; clearing big files in /var/log !" % usage,
              color="danger")
        os.path.walk('/var/log', delete_big_files, None)
        # Brutish way to restart all affected services.
        os.system('/sbin/reboot')
    elif usage > warning_threshold:
        print "High disk usage!"
        # Allow us to suppress this for machines with known, but stable, high
        # disk usage.
        if not os.path.exists('/home/lantern/suppress-disk-warnings'):
            alert("high-disk-usage",
                  details={'usage': usage},
                  text="Using %s%% of disk.\nPlease fix this or I'll delete big logs as soon as I reach %s%%." % (usage, critical_threshold))


if __name__ == '__main__':
    run()
