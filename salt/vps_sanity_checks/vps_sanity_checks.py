#!/usr/bin/env python

import os
import time

import mail_util
from redis_util import redis_shell


def srvs_in_cfgbysrv(dc, cfgbysrv):
    key = dc + ':slices'
    issues = [(srv, score)
              for srv, score in redis_shell.zrangebyscore(key,
                                                          '-inf',
                                                          '+inf',
                                                          withscores=True)
              if not srv.startswith('<empty')
              and srv not in cfgbysrv]
    for srv, score in issues[:]:
        # Double-check to avoid race conditions.
        if redis_shell.hexists('cfgbysrv', srv):
            issues.remove((srv, score))
        else:
            # Might as well fix it while we're at it!
            txn = redis_shell.pipeline()
            txn.zrem(key, srv)
            txn.zadd(key, '<empty:%s>' % score, score)
            txn.execute()
    return ["Server %s in %s's slice table but no config for it." % (srv, dc)
            for srv, _ in issues]

def configs_start_with_newline(cfgbysrv):
    """At some point we've found configurations that don't start with a newline.
    These will pass fallback checks, but they won't merge nicely into the config
    passed to users. Here we check against that."""
    return ["Server %s's config doesn't start with a newline" % srv
            for srv, cfg in cfgbysrv.iteritems()
            if not cfg.startswith("\n")]

def report(errors):
    if not errors:
        print "No errors."
        return
    print "Got errors:"
    for error in errors:
        print "   ", error
    mail_util.send_alarm("Sanity checks failed!", "\n".join(errors))

def run_all_checks():
    cfgbysrv = redis_shell.hgetall('cfgbysrv')
    report(configs_start_with_newline(cfgbysrv)
           + srvs_in_cfgbysrv('vltok1', cfgbysrv)
           + srvs_in_cfgbysrv('doams3', cfgbysrv))


if __name__ == '__main__':
    run_all_checks()
