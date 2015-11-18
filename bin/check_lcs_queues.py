"""Check LCServer queues in the config server, vs the list of live servers."""

from datetime import datetime
import os
import re
import subprocess
import sys

import redis
import yaml

from misc_util import memoized
try:
    import vultr_util as vu
    import vps_util
except ImportError:
    print
    print "*** vultr_util module not found.  Please add [...]/lantern_aws/lib to your PYTHONPATH"
    print
    raise
import digitalocean

@memoized
def do_vpss():
    do_token = os.environ['DO_TOKEN']
    mgr = digitalocean.Manager(token=do_token)
    return mgr.get_all_droplets()

@memoized
def r():
    url = os.getenv("REDISCLOUD_PRODUCTION_URL")
    if not url:
        raise RuntimeError("Error: You need to set a REDISCLOUD_PRODUCTION_URL env var.")
    return redis.from_url(url)

def ip_by_srv():
    return {v: k
            for k, v in r().hgetall("srvip->srv").iteritems()}

def open_servers(region):
    return sorted(r().zrangebyscore(region + ':slices', '-inf', '+inf'))

def queued_ips(region):
    return [cfg.split('|')[0] for cfg in r().lrange(region + ':srvq', 0, -1)]

def names_by_ip(dc):
    if dc.startswith('vl'):
        return {d['main_ip']: d['label']
                for d in vu.vultr.server_list(None).itervalues()}
    elif dc.startswith('do'):
        return {d.ip_address: d.name
                for d in do_vpss()}

def print_queued_server_ids(region):
    d = names_by_ip(region)
    key = region + ':srvq'
    queued_cfgs = r().lrange(key, 0, -1)
    for i, ip in enumerate(reversed(queued_ips(region))):
        print i+1, d.get(ip)
pq = print_queued_server_ids  # shortcut since I use this a lot.

def ssh(ip, cmd):
    return subprocess.check_output(['ssh', ip, '-o', 'StrictHostKeyChecking=no', cmd])

def load_avg(ip):
    return float(ssh(ip, 'uptime').split()[-1])

def access_data(ip):
    return ssh(ip, 'sudo cat /home/lantern/access_data.json')

def save_access_data(ip_list, filename="../../lantern/src/github.com/getlantern/flashlight/genconfig/fallbacks.json"):
    file(filename, 'w').write("[\n" + ",\n".join(map(access_data, ip_list)) + "\n]\n")


def vpss(provider_etc):
    return vps_util.vps_shell(provider_etc).all_vpss()

def unused_servers(cm):
    vv = set(vps
             for vps in vpss(cm)
             if vps.name.startswith('fp-%s-' % cm))
    ret = set()
    for v in vv:
        id_ = r().hget("srvip->srv", v.ip)
        if not id_ or not r().hget("srv->cfg", id_):
            ret.add(v)
    return ret

def today(cm):
    """The number of servers launched today."""
    todaystr = vps_util.todaystr()
    return sum(1 for x in r().lrange(cm + ':vpss', 0, -1)
               if ('-%s-' % todaystr) in x)

def reqq(region):
    return r().lrange(region + ':srvreqq', 0, -1)

def slices(region):
    """The list of slices in a region."""
    return r().zrangebyscore(region + ':slices', '-inf', '+inf')

def ddslices(region):
    """Deduplicate the slices table, effectively removing splits.

    This may make sense in a crisis where the datacenter server queue is
    low, or after having recycled many servers (these will be split as
    soon as they're full again, causing more fragmentation in general
    than in the same slice had been assigned to a fresh server.)"""
    s = slices(region)
    toremove = [slice
                for slice, next in zip(s, s[1:])
                if slice.startswith('<empty') and next.startswith('<empty')]
    if toremove:
        r().zrem(region + ':slices', *toremove)
    return toremove

def openings(region):
    """The number of openings in the slice table for this region."""
    return sum(1 for x in slices(region)
               if x.startswith('<empty'))

reip = re.compile(r"(\d+\.\d+\.\d+\.\d+):443")
def allips(txt):
    return reip.findall(txt)

def reboot(ip):
    import os
    os.system('ssh -o StrictHostKeyChecking=no %s "sudo reboot"' % ip)
