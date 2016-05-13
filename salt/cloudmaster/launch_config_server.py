#!/usr/bin/env python

import time

import do_util
import vps_util


def launch_config_server():
    # XXX: this doesn't perform a complete setup yet.
    name = vps_util.new_vps_name('cs', plan=vps_util.my_cm() + '_8GB')
    d = do_util.create_vps(name)
    if not vps_util.highstate_pid(name):
        print("Highstate not running yet; waiting for a bit just in case...")
        time.sleep(10)
    while vps_util.highstate_pid(name):
        print("Highstate still running...")
        time.sleep(10)

if __name__ == '__main__':
    launch_config_server()
