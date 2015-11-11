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
            for k, v in r().hgetall("srvbysrvip").iteritems()}

def open_servers(dc):
    return sorted(r().zrangebyscore(dc + ':slices', '-inf', '+inf'))

def existing_ips(dc, name_prefix=""):
    if dc.startswith("vl"):
        return set(d['main_ip']
                   for d in vu.vltr.server_list(None).itervalues()
                   if d['label'].startswith(name_prefix))
    elif dc.startswith("do"):
        return set(d.ip_address
                   for d in do_vpss()
                   if d.name.startswith(name_prefix))
    else:
        assert False

def check_queued_servers(dc, dry_run=True):
    key = dc + ':srvq'
    queued_cfgs = r().lrange(key, 0, -1)
    existing = existing_ips(dc)
    for i, cfg in enumerate(queued_cfgs):
        ip = cfg.split('|')[0]
        if ip not in existing:
            print "Non-existing ip %s in position %s" % (ip, i)
            if not dry_run:
                print r().lrem(key, cfg, 1)
                print

def queued_ips(dc):
    return [cfg.split('|')[0] for cfg in r().lrange(dc + ':srvq', 0, -1)]

def names_by_ip(dc):
    if dc.startswith('vl'):
        return {d['main_ip']: d['label']
                for d in vu.vultr.server_list(None).itervalues()}
    elif dc.startswith('do'):
        return {d.ip_address: d.name
                for d in do_vpss()}

def print_queued_server_ids(dc):
    d = names_by_ip(dc)
    key = dc + ':srvq'
    queued_cfgs = r().lrange(key, 0, -1)
    for i, ip in enumerate(reversed(queued_ips(dc))):
        print i+1, d.get(ip)
pq = print_queued_server_ids  # shortcut since I use this a lot.

def discard_ips(dc):
    ibs = ip_by_srv()
    open_ips = set(map(ibs.get, open_servers(dc)))
    return open_ips | set(queued_ips(dc))

def underused_vultr_vpss():
    dips = discard_ips('vltok1')
    vv = [x
          for x in vu.vultr.server_list(None).values()
          if x['label'].startswith('fp-jp-')
          and x['main_ip'] not in dips]
    vv.sort(key=lambda x: x['current_bandwidth_gb'])
    return vv

def ssh(ip, cmd):
    return subprocess.check_output(['ssh', ip, '-o', 'StrictHostKeyChecking=no', cmd])

def load_avg(ip):
    return float(ssh(ip, 'uptime').split()[-1])

def underused_do_vpss():
    dips = discard_ips('doams3')
    vv = [x
          for x in do_vpss()
          if x.name.startswith('fp-nl-')
          and x.ip_address not in dips]
    d = {x: load_avg(x.ip_address) for x in vv}
    vv.sort(key=d.get)
    return d, vv

def access_data(ip):
    return ssh(ip, 'sudo cat /home/lantern/access_data.json')

def save_access_data(ip_list, filename="../../lantern/src/github.com/getlantern/flashlight/genconfig/fallbacks.json"):
    file(filename, 'w').write("[\n" + ",\n".join(map(access_data, ip_list)) + "\n]\n")

def unused_servers(dc):
    if dc.startswith('vl'):
        prefix = "fp-jp-"
    elif dc.startswith('do'):
        prefix = "fp-nl-"
    else:
        assert False
    ips = set(existing_ips(dc, name_prefix=prefix)) - set(queued_ips(dc))
    ret = set()
    for ip in ips:
        id_ = r().hget("srvbysrvip", ip)
        if not id_ or not r().hget("cfgbysrv", id_):
            ret.add(ip)
    return ret

def remove_fp(dc, ip):
    for cfg in r().hgetall('cfgbysrv').itervalues():
        if cfg.split('|')[0] == ip:
            print "deleting one config..."
            r().lrem('cfgbysrv', cfg, 0)
            r().incr('cfgbysrv:version')
    print r().lrem(dc + ':vpss', names_by_ip(dc)[ip], 0)
    r().incr(dc + ':vpss:version')


def today(dc):
    """The number of servers launched today."""
    todaystr = vps_util.todaystr()
    return sum(1 for x in r().lrange(dc + ':vpss', 0, -1)
               if ('-%s-' % todaystr) in x)

def reqq(dc):
    return r().lrange(dc + ':srvreqq', 0, -1)

def slices(dc):
    """The list of slices in a dc."""
    return r().zrangebyscore(dc + ':slices', '-inf', '+inf')

def ddslices(dc):
    """Deduplicate the slices table, effectively removing splits.

    This may make sense in a crisis where the datacenter server queue is
    low, or after having recycled many servers (these will be split as
    soon as they're full again, causing more fragmentation in general
    than in the same slice had been assigned to a fresh server.)"""
    s = slices(dc)
    toremove = [slice
                for slice, next in zip(s, s[1:])
                if slice.startswith('<empty') and next.startswith('<empty')]
    if toremove:
        r().zrem(dc + ':slices', *toremove)
    return toremove

def openings(dc):
    """The number of openings in the slice table for this dc."""
    return sum(1 for x in slices(dc)
               if x.startswith('<empty'))

reip = re.compile(r"(\d+\.\d+\.\d+\.\d+):443")
def allips(txt):
    return reip.findall(txt)

def reboot(ip):
    import os
    os.system('ssh -o StrictHostKeyChecking=no %s "sudo reboot"' % ip)
