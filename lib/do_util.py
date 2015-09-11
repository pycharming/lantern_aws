import os
import subprocess
import time

import digitalocean
import yaml

import vps_util


ssh_tmpl = "ssh -o StrictHostKeyChecking=no -i /etc/salt/cloudmaster.id_rsa root@%s '%%s'"
fetchaccessdata_tmpl = "scp -o StrictHostKeyChecking=no -i /etc/salt/cloudmaster.id_rsa root@%s:/home/lantern/access_data.json ."

do_token = os.getenv("DO_TOKEN")
do = digitalocean.Manager(token=do_token)


def create_vps(name):
    vps_util.save_pillar(name)
    out = subprocess.check_output(["salt-cloud", "-p", "do_nl_1GB", name])
    # Uberhack; It'll get better with newer salt-cloud versions.
    d = yaml.load(out[out.rfind(name + ":"):].replace("----------", "")).values()[0]
    return d['name'], d['ip_address']


def init_vps(name_and_ip, wait_for_hs=True):
    name, ip = name_and_ip
    if wait_for_hs:
        while not vps_util.highstate_pid(name):
            print("Highstate not running yet...")
            time.sleep(10)
    while vps_util.highstate_pid(name):
        print("Highstate still running...")
        time.sleep(10)
    print("Highstate done!")
    return vps_util.hammer_the_damn_thing_until_it_proxies(
        name,
        ssh_tmpl % ip,
        fetchaccessdata_tmpl % ip)

def destroy_vps(name):
    os.system('salt-cloud -yd ' + name)
    os.system('salt-key -yd' + name)
