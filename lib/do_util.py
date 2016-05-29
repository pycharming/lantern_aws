import os
import subprocess
import sys
import time

import digitalocean
import requests
import yaml

import misc_util
import vps_util


do_token = os.getenv("DO_TOKEN")
do = digitalocean.Manager(token=do_token)

dc2location = {'ams3': 'Amsterdam 3',
               'nyc3': 'New York 3',
               'sfo1': 'San Francisco 1',
               'sgp1': 'Singapore 1'}

def create_vps(name, req={}, plan=None):
    vps_util.save_pillar(name, req)
    if plan is None:
        plan = vps_util.dc_by_cm(vps_util.my_cm()) + "_512MB"
    dc, size = plan.split('_')
    location = dc2location[dc]
    d = digitalocean.Droplet(token=do_token,
                             name=name,
                             size=size,
                             image="14.04.4 x64",
                             region=location,
                             ssh_keys="cloudmaster",
                             backups=False,
                             ipv6=True,
                             private_networking=True)
    print "Creating droplet..."
    d.create()
    print "Waiting for droplet to start up..."
    assert len(d.action_ids) == 1
    action = d.get_action(d.action_ids[0])
    action.wait(20)
    print "Creation completed, fetching droplet data..."
    d.load()
    assert d.name == name
    return {'name': name, 'ip': d.ip_address, 'droplet': d}

def init_vps(d):
    name = d['name']
    ip = d['ip']
    if not vps_util.highstate_pid(name):
        print("Highstate not running yet; waiting for a bit just in case...")
        time.sleep(10)
    while vps_util.highstate_pid(name):
        print("Highstate still running...")
        time.sleep(10)
    print("Highstate done!")
    return vps_util.hammer_the_damn_thing_until_it_proxies(name)

def droplets_by_name():
    return {d.name: d
            for d in do.get_all_droplets()}

dbn_cache=misc_util.Cache(timeout=60*60, update_fn=droplets_by_name)

def destroy_vps(name):
    try:
        droplet = dbn_cache.get()[name]
        # We use the DO API directly and not salt-cloud here because the latter
        # takes forever and generates lots of API requests, which may make us run
        # out of our per-hour quota in busy times.
        requests.delete('https://api.digitalocean.com/v2/droplets/%s' % droplet.id,
                        headers={"Authorization": "Bearer " + do_token})
    except KeyError:
        print >> sys.stderr, "Droplet not found:", name
    os.system('salt-key -yd ' + name)

def droplet2vps(d):
    url = "https://cloud.digitalocean.com/droplets/%s/graphs" % d.id
    return vps_util.vps(d.name, d.ip_address, d.memory, 'do', url, d)

def all_vpss():
    return map(droplet2vps, do.get_all_droplets())
