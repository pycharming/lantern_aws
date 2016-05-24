from collections import defaultdict
import os
import subprocess
import sys
import time

import linode.api
import yaml

import vps_util


li = linode.api.Api(key=os.getenv("LINODE_APIKEY"))
li_tokyo = linode.api.Api(key=os.getenv("LINODE_TOKYO_APIKEY"))


def create_vps(name, req={}, plan=None):
    vps_util.save_pillar(name, req)
    if plan is None:
        plan = vps_util.dc_by_cm(vps_util.my_cm()) + "_1GB"
    out = subprocess.check_output(["salt-cloud", "-p", plan, name])
    # Uberhack: XXX update with salt version...
    d = yaml.load(out[out.rfind(name + ":"):].replace("----------", "").replace("|_", "-")).values()[0]
    return {'name': d['name'],
            'ip': d['public_ips'][0]}

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

def destroy_vps(name):
    ret = os.system('salt-cloud -yd ' + name)

def all_vpss():
    ipbyid = defaultdict(list)
    for l in li.linode_ip_list() + li_tokyo.linode_ip_list():
        if l['ISPUBLIC'] == 1:
            ipbyid[l['LINODEID']].append(l['IPADDRESS'])
    for k, v in ipbyid.items():
        if len(v) != 1:
            print >> sys.stderr, "*** WARNING: linode %s has %s public IPs. ***" % (k, len(v))
            print >> sys.stderr, "Picking an arbitrary one!"
        ipbyid[k] = v[0]
    ret = []
    for d in li.linode_list() + li_tokyo.linode_list():
        name = d['LABEL']
        url = "https://manager.linode.com/linodes/dashboard/%s" % name
        ret.append(vps_util.vps(name, ipbyid[d['LINODEID']], d['TOTALRAM'], 'li', url, d))
    return ret
