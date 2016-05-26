from __future__ import division

import multiprocessing

import yaml

from misc_util import defaultobj, pssh
from redis_util import redis_shell
import vps_util


def make_cache():
    return defaultobj(lambda: None)

def check_srv2cfg(interactive=False, cache=None):
    "All cfg entries point to proxies that are ours, and access_data matches."
    if cache is None:
        cache = make_cache()
    errors = []
    cache.vpss = cache.vpss or vps_util.all_vpss()
    cache.srv2cfg = cache.srv2cfg or redis_shell.hgetall('srv->cfg')
    # With configs YAML-parsed.
    cache.srv2cfgd = cache.srv2cfgd or {srv: yaml.load(cfg).values()[0]
                                        for srv, cfg in cache.srv2cfg.iteritems()}
    srv2ip = {srv: cfgd['addr'].split(':')[0]
              for srv, cfgd in cache.srv2cfgd.iteritems()}
    vps_ips = set(f.ip for f in cache.vpss)
    badipentries = {srv: ip
                    for srv, ip in srv2ip.iteritems()
                    if ip not in vps_ips}
    if badipentries:
        errors.append(('bad IP in srv->cfg', badipentries))
    badips = set(badipentries.values())
    cache.ips2check = cache.ips2check or [ip for ip in srv2ip.values() if ip not in badips]
    cache.pool = cache.pool or multiprocessing.Pool(50)
    if cache.access_datas is None:
        status, outputs = map(list,
                              zip(*pssh(cache.ips2check,
                                        'cat /home/lantern/access_data.json',
                                        pool=cache.pool)))
        bad = [i for i, s in enumerate(status) if s != 0]
        go_on = True
        while bad:
            print "%s bad SSH results:" % len(bad)
            for i in bad:
                print "    %s:" % cache.ips2check[i]
                print "        status: %s" % status[i]
                print "        output: %r" % outputs[i]
            if interactive:
                go_on = confirm('%s bad IPs; retry?' % len(bad))
            if go_on:
                retry_result = pssh([cache.ips2check[i] for i in bad],
                                    'cat /home/lantern/access_data.json',
                                    pool=cache.pool)
                new_bad = []
                for i, (s, o) in zip(bad, retry_result):
                    if s == 0:
                        status[i] = s
                        outputs[i] = o
                    else:
                        new_bad.append(i)
                go_on = len(new_bad) != len(bad)
                bad = new_bad
            else:
                if interactive and confirm("Abort? ('n' will just treat the rest as unparseable)"):
                    raise RuntimeError("Bad SSH replies")
                else:
                    break
        cache.access_datas = outputs
    adbyip = {}
    unparsable = []
    for ip, ad in zip(cache.ips2check, cache.access_datas):
        try:
            adbyip[ip] = json.loads(ad)
        except:
            traceback.print_exc()
            unparsable.append((ip, ad))
    if unparsable:
        errors.append(('unparsable access data', unparsable))
    ad_mismatches = []
    for srv, ip in srv2ip.iteritems():
        if ip in adbyip:
            cfgd = cache.srv2cfgd[srv]
            proxyd = adbyip[ip]
            for k, v in proxyd.iteritems():
                if str(cfgd.get(k)).strip() != str(v).strip():
                    ad_mismatches.append((srv, ip, k, v, cfgd.get(k)))
    if ad_mismatches:
        errors.append(('srv->cfg access data mismatch', ad_mismatches))
    return errors
