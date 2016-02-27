#!/usr/bin/env python

import os
import time

import mail_util
from redis_util import redis_shell


def srvs_in_cfgbysrv(region, cfgbysrv):
    key = region + ':slices'
    issues = [(srv, score)
              for srv, score in redis_shell.zrangebyscore(key,
                                                          '-inf',
                                                          '+inf',
                                                          withscores=True)
              if not srv.startswith('<empty')
              and not srv.startswith('<locked')
              and srv not in cfgbysrv]
    for srv, score in issues[:]:
        # Double-check to avoid race conditions.
        if redis_shell.hexists('srv->cfg', srv):
            issues.remove((srv, score))
        else:
            # Might as well fix it while we're at it!
            txn = redis_shell.pipeline()
            txn.zrem(key, srv)
            txn.zadd(key, '<empty:%s>' % score, score)
            txn.execute()
    return ["Server %s in %s's slice table but no config for it." % (srv, region)
            for srv, _ in issues]

def configs_start_with_newline(cfgbysrv):
    """At some point we've found configurations that don't start with a newline.
    These will pass fallback checks, but they won't merge nicely into the config
    passed to users. Here we check against that."""
    return ["Server %s's config doesn't start with a newline" % srv
            for srv, cfg in cfgbysrv.iteritems()
            if not cfg.startswith("\n")]

def check_srvq_size(region):
    size = redis_shell.llen(region + ':srvq')
    if size < 20:
        return ["Server queue for region '%s' has %s servers only."
                % (region, size)]
    else:
        return []

def fallback_srvs_in_srv_table(region, cfgbysrv):
    if redis_shell.get(region + ':fallbacksrv') in cfgbysrv:
        return []
    else:
        return ["Fallback server for region '%s' is not in srv->cfg" % region]

def report(errors):
    if not errors:
        print "No errors."
        return
    print "Got errors:"
    for error in errors:
        print "   ", error
    mail_util.send_alarm("Sanity checks failed!", "\n".join(errors))

def run_all_checks():
    cfgbysrv = redis_shell.hgetall('srv->cfg')
    errors = configs_start_with_newline(cfgbysrv)
    regions = redis_shell.smembers('user-regions')
    for region in regions:
        errors.extend(srvs_in_cfgbysrv(region, cfgbysrv))
    for region in regions:
        errors.extend(check_srvq_size(region))
    for region in regions:
        errors.extend(fallback_srvs_in_srv_table(region, cfgbysrv))
    report(errors)


if __name__ == '__main__':
    run_all_checks()
