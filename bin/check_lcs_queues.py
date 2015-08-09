"""Check LCServer queues in the config server, vs the list of live servers."""

import os
import subprocess

import redis

import do_fps as do
import util
import vultr_util as vu


@util.memoized
def r():
    url = os.getenv("REDISCLOUD_PRODUCTION_URL")
    if not url:
        raise RuntimeError("Error: You need to set a REDISCLOUD_PRODUCTION_URL env var.")
    return redis.from_url(url)

def ip_by_srv():
    return {v: k
            for k, v in r().hgetall("srvbysrvip").iteritems()}

def srv_by_dc(dc):
    return list(sorted(k
                       for k, v in r().hgetall("dcbysrv").iteritems()
                       if v == dc))

def open_servers(dc):
    return sorted(r().zrangebyscore(dc + ':slices', '-inf', '+inf'))

def existing_ips(dc):
    if dc.startswith("vl"):
        return set(d['main_ip']
                   for d in vu.vltr.server_list(None).itervalues())
    elif dc.startswith("do"):
        return set(d.ip_address
                   for d in do.droplets_by_name.itervalues())
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

def print_queued_server_ids(dc):
    if dc.startswith('vl'):
        d = {d['main_ip']: d['label']
             for d in vu.vltr.server_list(None).itervalues()}
    elif dc.startswith('do'):
        d = {d.ip_address: name
             for name, d in do.droplets_by_name.iteritems()}
    key = dc + ':srvq'
    queued_cfgs = r().lrange(key, 0, -1)
    for i, cfg in enumerate(reversed(queued_cfgs)):
        ip = cfg.split('|')[0]
        print i+1, d.get(ip)
pq = print_queued_server_ids  # shortcut since I use this a lot.

def discard_ips(dc):
    ibs = ip_by_srv()
    open_ips = set(map(ibs.get, open_servers(dc)))
    queued_ips = set(cfg.split('|')[0] for cfg in r().lrange(dc + ':srvq', 0, -1))
    return open_ips | queued_ips

def underused_vultr_vpss():
    dips = discard_ips('vltok1')
    vv = [x
          for x in vu.vltr.server_list(None).values()
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
          for name, x in do.droplets_by_name.iteritems()
          if name.startswith('fp-nl-')
          and x.ip_address not in dips]
    d = {x: load_avg(x.ip_address) for x in vv}
    vv.sort(key=d.get)
    return d, vv

def access_data(ip):
    return ssh(ip, 'sudo cat /home/lantern/access_data.json')

def save_access_data(ip_list, filename="../../lantern/src/github.com/getlantern/flashlight/genconfig/fallbacks.json"):
    file(filename, 'w').write("[\n" + ",\n".join(map(access_data, ip_list)) + "\n]\n")
