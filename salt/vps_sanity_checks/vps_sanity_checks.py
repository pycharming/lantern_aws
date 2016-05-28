#!/usr/bin/env python

# XXX: unify cache concept.

from collections import defaultdict
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

def srv2cfg_consistent_with_vps_list(srv2cfg=None, cache=None):
    if cache is None:
        cache = model.make_cache()
    # XXX contrived because of legacy reasons; I'll clean it up soon(TM)...
    cache.srv2cfg = cache.srv2cfg or srv2cfg or redis_shell.hgetall('srv->cfg')
    cache.all_vpss = cache.all_vpss or vps_util.all_vpss()
    errors = model.check_srv2cfg(cache=cache)
    for err_type, err_cases in errors:
        if err_type == 'bad IP in srv->cfg':
            # Delete entries pointing to proxies that are no longer ours.
            names = redis_shell.hmget('srv->name', err_cases.keys())
            for name, (srv, ip) in zip(names, err_cases.iteritems()):
                try:
                    print "Retiring", name, ip, srv
                    vps_util.actually_retire_proxy(name=name, ip=ip, srv=srv)
                except:
                    alert_exception("retire non-existing proxy %s (%s), srvid %s" % (name, ip, srv))
    return errors

def no_duplicate_names(cache=None):
    if cache is None:
        cache = make_cache()
    cache.all_vpss = cache.all_vpss or vps_util.all_vpss()
    by_name = defaultdict(list)
    for v in cache.all_vpss:
        by_name[v.name].append(v)
    duplicates = []
    for name, vpss in by_name.iteritems():
        if len(vpss) > 1:
            duplicates.append((name, [v.ip for v in vpss]))
    if duplicates:
        return [('duplicate names', duplicates)]
    else:
        return []

def srvq_integrity(region, cache=None):
    """
    perform sanity checks on the region's server queue.

    (i) all VPSs listed there actually exist.

    (ii) the IPs and names of the VPSs match those recorded in the queue.

    An actual proxying check is not performed. As of this writing, there's a
    ticket to make checkfallbacks do that.

    This assumes that you have checked for duplicate proxies.
    """
    if cache is None:
        cache = model.make_cache()
    if cache.srvq is None:
        cache.srvq = {}
    if region not in cache.srvq:
        cache.srvq[region] = redis_shell.lrange(region + ':srvq', 0, -1)
    cache.all_vpss = cache.all_vpss or vps_util.all_vpss()
    vps_by_name = {v.name: v for v in cache.all_vpss}
    not_ours = []
    bad_ip = []
    for entry in cache.srvq[region]:
        ip, name, cfg = entry.split('|')
        if name not in vps_by_name:
            not_ours.append((ip, name, entry))
            # XXX: factor out fixes from here.
            redis_shell.lrem(region + ':srvq', entry)
            continue
        actual_ip = vps_by_name[name].ip
        if actual_ip != ip:
            # XXX: factor out fixes from here.
            redis_shell.lrem(region + ':srvq', entry)
            bad_ip.append((ip, actual_ip, name, entry))
    ret = []
    if not_ours:
        ret.append(('Queued proxy no longer ours', not_ours))
    if bad_ip:
        ret.append(('Inconsistent IP in queued proxy', bad_ip))
    return ret

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

def srvq_size(region):
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
    print "Performing checks..."
    cache = model.make_cache()
    # This is new code, so let's test it in a cushion to start with.
    try:
        print "Checking that srv->cfg table is consistent with the VPS listing..."
        errors = srv2cfg_consistent_with_vps_list(srv2cfg, cache)
    except:
        alert_exception("trying to check consistency between srv->cfg and all_vpss")
        errors = []
    try:
        print "Check that we don't have duplicate names"
        errors.extend(no_duplicate_names(cache))
    except:
        alert_exception("trying to check for duplicate VPS names")
    print "Checking that configs start with a newline..."
    errors.extend(configs_start_with_newline(srv2cfg))
    regions = redis_shell.smembers('user-regions')
    print "Checking that slice server entries are in srv->cfg..."
    for region in regions:
        print "    (region %s)..." % region
        errors.extend(slice_srvs_in_srv2cfg(region, srv2cfg))
    print "Checking server queue size..."
    for region in regions:
        print "    (region %s)..." % region
        errors.extend(srvq_size(region))
    print "Checking server queue integrity..."
    for region in regions:
        print "    (region %s)..." % region
        try:
            errors.extend(srvq_integrity(region, cache=cache))
        except:
            alert_exception("trying to check server queue integrity")
    print "Check that regional fallbacks and honeypots are in srv->cfg..."
    for region in regions:
        print "    (region %s)..." % region
        errors.extend(fallbacks_and_honeypots_in_srv_table(region, srv2cfg))
    report(errors)


if __name__ == '__main__':
    run_all_checks()
