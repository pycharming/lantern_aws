import os
import subprocess
import time

import digitalocean
import yaml

import vps_util


reboot_tmpl = "ssh -o StrictHostKeyChecking=no -i /etc/salt/cloudmaster.id_rsa root@%s reboot"
fetchaccessdata_tmpl = "scp -o StrictHostKeyChecking=no -i /etc/salt/cloudmaster.id_rsa root@%s:/home/lantern/access_data.json ."

do_token = os.getenv("DO_TOKEN")
do = digitalocean.Manager(token=do_token)


def create_vps(name):
    vps_util.save_pillar(name)
    out = subprocess.check_output(["salt-cloud", "-p", "do_nl_1GB", name])
    # Uberhack; It'll get better with newer salt-cloud versions.
    d = yaml.load(out[out.rfind(name + ":"):].replace("----------", "")).values()[0]
    return d['name'], d['ip_address']

def highstate_running(name):
    out = subprocess.check_output(["salt", name, "state.running"])
    return len(out.strip().split('\n')) > 1

def init_vps((name, ip), wait_for_hs=True):
    if wait_for_hs:
        while not highstate_running(name):
            print "Highstate not running yet..."
            time.sleep(10)
    while highstate_running(name):
        print "Highstate still running..."
        time.sleep(10)
    print "Highstate done!"
    return vps_util.hammer_the_damn_thing_until_it_proxies(
        name,
        reboot_tmpl % ip,
        fetchaccessdata_tmpl % ip)

def destroy_vps(name):
    os.system('salt-cloud -yd ' + name)
    os.system('salt-key -yd' + name)
