#!/usr/bin/env python

import os.path
import time
import traceback

import psutil

from alert import alert


# In percentage of disk usage.
# This may seem low, but psutil percentages are actually some 5% lower than
# those reported by `df`, so I'm being a bit conservative here.
critical_threshold = 90
# Files larger than this will be removed when we hit critical usage. This
# figure was chosen to keep syslog rotations that haven't exceeded their
# prescribed size (200 MB, at the time of this writing) by more than 20%.
max_size = 240 * 1024 * 1024
# In seconds
report_period = 60 * 60

suppress_path = '/home/lantern/suppress-disk-warnings'
last_warning_time_path = '/home/lantern/last-disk-warning-time'


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
    if usage < critical_threshold:
        return
    print "Disk usage *critical*; clearing big files in /var/log and rebooting!"
    alert("disk-usage-critical",
            details={'usage': usage},
            text="Using %s%% of disk; clearing big files in /var/log !" % usage,
            color="danger")
    os.path.walk('/var/log', delete_big_files, None)
    # Brutish way to restart all affected services.
    os.system('/sbin/reboot -f')


if __name__ == '__main__':
    run()
