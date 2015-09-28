# Note this requires python3!

import multiprocessing as mp
from pprint import pprint as pp
from imp import reload
import subprocess
import traceback

from redis_util import redis_shell
import vps_util
import vultr_util as vu
import do_util as do


class vps:

    def ssh(self, cmd, timeout=300):
        try:
            return toascii(subprocess.check_output(['ssh',
                                                    '-o', 'StrictHostKeyChecking=no',
                                                    self.ip,
                                                    'sudo ' + cmd + " 2>&1"],
                                                   timeout=timeout))
        except subprocess.CalledProcessError:
            return traceback.format_exc()
        except subprocess.TimeoutExpired:
            return "<timed out>"

    def __repr__(self):
        return "<%s (%s)>" % (self.name, self.ip)

class vultr_vps(vps):

    def __init__(self, vultr_dict):
        self.name = vultr_dict['label']
        self.ip = vultr_dict['main_ip']
        self.vultr_dict = vultr_dict

    def is_chained(self):
        return self.name.startswith('fp-')

    def reclass(self, new_histate):
        return new_histate.vultr_vps(self.vultr_dict)

class do_vps(vps):

    def __init__(self, droplet):
        self.name = droplet.name
        self.ip = droplet.ip_address
        self.droplet = droplet

    def is_chained(self):
        return self.name.startswith('fp-nl-')

    def reclass(self, new_histate):
        return new_histate.do_vps(self.droplet)

def toascii(b):
    if isinstance(b, str):
        return b
    else:
        return b.decode('ascii')

def get_registered_vpss():
    return set(map(toascii, (redis_shell.lrange('doams3:vpss', 0, -1)
                             + redis_shell.lrange('vltok1:vpss', 0, -1))))

def get_actual_vpss():
    return (list(map(vultr_vps, vu.vultr.server_list(None).values()))
            + list(map(do_vps, do.do.get_all_droplets())))

def check_highstate(vps):
    print("Starting check_highstate on", vps, "...")
    return vps.ssh("grep CAMEL /opt/ts/etc/trafficserver/records.config || echo -n AW")

def histate(vps):
    print("Starting histate on", vps, "...")
    return vps.ssh("salt-call state.highstate")

def rehi(pair):
    print("Rehistating", pair, "...")
    vps, msg = pair
    m = vps_util.highstate_re.search(toascii(msg))
    if m:
        return vps.ssh("kill -9 %s ; sudo salt-call state.highstate" % m.groups()[0])
    else:
        return "No PID."

def turn_off_salt_minion(vps):
    print("Turning off %s..." % vps)
    # check vs 'salt-minion stop/waiting\n'
    return vps.ssh("service salt-minion stop")

def check_salt_minion_off(vps):
    print("Checking minion process in %s..." % vps)
    return vps.ssh("service salt-minion status")

def remove_salt(vps):
    print("Removing salt from %s..." % vps)
    # check vs ''
    return vps.ssh("rm -rf /etc/salt /usr/bin/salt /usr/bin/salt-call /usr/bin/salt-minion /usr/lib/python2.7/dist-packages/salt /usr/lib/python2.7/dist-packages/salt-2014.7.0.egg-info")

def download_bootstrap(vps):
    print("Downloading bootstrap into %s..." % vps)
    # check that it has "184k"
    return vps.ssh("rm bootstrap-salt.sh ; curl -L https://raw.githubusercontent.com/saltstack/salt-bootstrap/902da734465798edb3aa6a68445ada358a69b0ef/bootstrap-salt.sh -o bootstrap-salt.sh")

def install_salt(vps):
    print("Installing salt on %s..." % vps)
    # XXX: 10.99.0.119 for Vultr
    # check that it ends with "*  INFO: Salt installed!\n"
    return vps.ssh("sh ./bootstrap-salt.sh -A 10.133.46.205 -i %s git v2015.5.5" % vps.name)

ipno = 1

def configure_vultr_private_network(vps):
    global ipno
    print("Configuring private networking for %s..." % vps)
    ipno += 1
    lo = ipno % 255
    hi = ipno // 255
    if lo == 255:
        lo = 2
        hi += 1
        ipno += 2
    return vps.ssh(" -u aranhoide echo "" > tmp "
                   + "".join(" && echo '%s' >> tmp " % line for line in vultr_private_net_cfg_tmpl.split("\n")) % (hi, lo)
                   + " && cat /etc/network/interfaces tmp > tmp2 && sudo mv tmp2 /etc/network/interfaces && echo Done. ")

def already_configured(vps):
    print("Checking whether private networking is already confiured for %s..." % vps)
    return vps.ssh("grep 'auto eth1' /etc/network/interfaces")

vultr_private_net_cfg_tmpl = """
auto eth1
iface eth1 inet static
    address 10.99.%s.%s
    netmask 255.255.0.0
            mtu 1450
"""

def restart_salt(vps):
    print("Restarting salt at", vps, "...")
    return vps.ssh("service salt-minion restart")

def run():
    reg_vpss = get_registered_vpss()
    return [x for x in get_actual_vpss() if x.is_chained() and x.name in reg_vpss]

