import os
import subprocess
import time

import digitalocean
import requests
import yaml

import misc_util
import vps_util


ssh_tmpl = "ssh -o StrictHostKeyChecking=no -i /etc/salt/cloudmaster.id_rsa root@%s '%%s'"
fetchaccessdata_tmpl = "scp -o StrictHostKeyChecking=no -i /etc/salt/cloudmaster.id_rsa root@%s:/home/lantern/access_data.json ."

do_token = os.getenv("DO_TOKEN")
do = digitalocean.Manager(token=do_token)


def create_vps(name):
    vps_util.save_pillar(name)
    out = subprocess.check_output(["salt-cloud", "-p", "do_nl_1GB", name])
    # Uberhack: XXX update with salt version...
    d = yaml.load(out[out.rfind(name + ":"):].replace("----------", "").replace("|_", "-")).values()[0]
    return d['name'], d['networks']['v4'][1]['ip_address']

def init_vps(name_and_ip):
    name, ip = name_and_ip
    if not vps_util.highstate_pid(name):
        print("Highstate not running yet; waiting for a bit just in case...")
        time.sleep(10)
    while vps_util.highstate_pid(name):
        print("Highstate still running...")
        time.sleep(10)
    print("Highstate done!")
    return vps_util.hammer_the_damn_thing_until_it_proxies(
        name,
        ssh_tmpl % ip,
        fetchaccessdata_tmpl % ip)

def droplets_by_name():
    return {d.name: d
            for d in do.get_all_droplets()}

dbn_cache=misc_util.Cache(timeout=60*60, update_fn=droplets_by_name)

def destroy_vps(name):
    droplet = dbn_cache.get()[name]
    # We use the DO API directly and not salt-cloud here because the latter
    # takes forever and generates lots of API requests, which may make us run
    # out of our per-hour quota in busy times.
    requests.delete('https://api.digitalocean.com/v2/droplets/%s' % droplet.id,
                    headers={"Authorization": "Bearer " + do_token})
    os.system('salt-key -yd' + name)
