# Note this requires python3!

import multiprocessing
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

def run():
    reg_vpss = get_registered_vpss()
    rest = [x for x in get_actual_vpss() if x.is_chained() and x.name in reg_vpss]
    return rest
#    with multiprocessing.Pool(50) as pool:
#        status = pool.map(check_highstate, rest)
#    pairs = [(v, s) for v, s in zip(rest, status) if "CAMELLIA" not in s]
#    return [x[0] for x in pairs], [x[1] for x in pairs]
