#!/usr/bin/env python

import time

import requests

import do_util
import vps_util


def launch_config_server():
    # XXX: this doesn't perform a complete setup yet.
    name = vps_util.new_vps_name('cs')
    d = do_util.create_vps(name, plan=vps_util.dc_by_cm(vps_util.my_cm()) + '_2GB')
    if not vps_util.highstate_pid(name):
        print("Highstate not running yet; waiting for a bit just in case...")
        time.sleep(10)
    while vps_util.highstate_pid(name):
        print("Highstate still running...")
        time.sleep(10)
    ip = d['ip']
    print "Checking for completion..."
    while True:
        try:
            resp = requests.get(('http://%s/proxies.yaml.gz' % ip),
                                timeout=5)
            if resp.ok:
                break
        except requests.exceptions.RequestException:
            pass
        print "Server setup not complete yet; retrying..."
        time.sleep(5)
    print "%s (%s) is up."  % (name, ip)

if __name__ == '__main__':
    launch_config_server()
