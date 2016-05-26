#!/usr/bin/env python

import traceback

import alert
import model
from redis_util import redis_shell
import vps_util


def alert_exception(op):
    traceback.print_exc()
    alert.send_to_slack(
        "**Exception** trying to %s" % op,
        ("The following exception happened while trying to %s:\n%s"
         % (op, traceback.format_exc())),
        color='danger')

def srv2cfg_consistent_with_vps_list(srv2cfg, all_vpss, cache=None):
    if cache is None:
        cache = model.make_cache()
    cache.srv2cfg = srv2cfg
    cache.all_vpss = all_vpss
    errors = model.check_srv2cfg(cache=cache)
    for err_type, err_cases in errors:
        if err_type == 'bad IP in srv->cfg':
            names = redis_shell.hmget('srv->name', err_cases.keys())
            for name, (srv, ip) in zip(names, err_cases.iteritems()):
                try:
                    print "Retiring", name, ip, srv
                    vps_util.actually_retire_proxy(name=name, ip=ip, srv=srv)
                except:
                    alert_exception("retire non-existing proxy %s (%s), srvid %s" % (name, ip, srv))
    return errors

def slice_srvs_in_srv2cfg(region, srv2cfg):
    key = region + ':slices'
    issues = [(k, score)
              for k, score in redis_shell.zrangebyscore(key,
                                                          '-inf',
                                                          '+inf',
                                                          withscores=True)
              if not k.startswith('<empty')
              and not k.startswith('<locked')
              and k.split('|')[0] not in srv2cfg]
    for k, score in issues[:]:
        # Double-check to avoid race conditions.
        if redis_shell.hexists('srv->cfg', k.split('|')[0]):
            issues.remove((k, score))
        else:
            # Might as well fix it while we're at it!
            txn = redis_shell.pipeline()
            txn.zrem(key, k)
            txn.zadd(key, '<empty:%s>' % int(score), score)
            txn.execute()
    return ["Key %s in %s's slice table but no config for it." % (k, region)
            for k, _ in issues]

def configs_start_with_newline(srv2cfg):
    """At some point we've found configurations that don't start with a newline.
    These will pass fallback checks, but they won't merge nicely into the config
    passed to users. Here we check against that."""
    return ["Server %s's config doesn't start with a newline" % srv
            for srv, cfg in srv2cfg.iteritems()
            if not cfg.startswith("\n")]

def check_srvq_size(region):
    size = redis_shell.llen(region + ':srvq')
    if size < 20:
        return ["Server queue for region '%s' has %s servers only."
                % (region, size)]
    else:
        return []

def fallbacks_and_honeypots_in_srv_table(region, srv2cfg):
    ret = []
    for srv in redis_shell.smembers(region + ':fallbacks'):
        if srv not in srv2cfg:
            ret.append("Fallback server %s for region %s is not in srv->cfg" % (srv, region))
    for srv in redis_shell.smembers(region + ':honeypots'):
        if srv not in srv2cfg:
            ret.append("Honeypot server %s for region %s is not in srv->cfg" % (srv, region))
    return ret

def report(errors):
    if not errors:
        print "No errors."
        return
    print "Got errors:"
    for error in errors:
        print "   ", error
    alert.alert(type='sanity-check-failures',
                details={'errors': errors},
                text='\n'.join(map(str, errors)),
                color='danger')

def run_all_checks():
    print "Fetching config data..."
    srv2cfg = redis_shell.hgetall('srv->cfg')
    print "Fetching VPS data..."
    all_vpss = vps_util.all_vpss()
    print "Performing checks..."
    # This is new code, so let's test it in a cushion to start with.
    try:
        errors = srv2cfg_consistent_with_vps_list(srv2cfg, all_vpss)
    except:
        alert_exception("trying to check consistency between srv->cfg and all_vpss")
        errors = []
    errors.extend(configs_start_with_newline(srv2cfg))
    regions = redis_shell.smembers('user-regions')
    for region in regions:
        errors.extend(slice_srvs_in_srv2cfg(region, srv2cfg))
    for region in regions:
        errors.extend(check_srvq_size(region))
    for region in regions:
        errors.extend(fallbacks_and_honeypots_in_srv_table(region, srv2cfg))
    report(errors)


if __name__ == '__main__':
    run_all_checks()
