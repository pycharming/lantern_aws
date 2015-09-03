#!/usr/bin/env python

import time

import mail_util
from redis_util import redis_shell


def srvs_in_cfgbysrv(dc, cfgbysrv):
    return ["Server %s in %s's slice table but no config for it." % (srv, dc)
            for srv in redis_shell.zrangebyscore(dc + ':slices', '-inf', '+inf')
            if srv not in cfgbysrv]

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
