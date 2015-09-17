#!/usr/bin/env python

import os
import time

import mail_util
from redis_util import redis_shell


def srvs_in_cfgbysrv(dc, cfgbysrv):
    return ["Server %s in %s's slice table but no config for it." % (srv, dc)
            for srv in redis_shell.zrangebyscore(dc + ':slices', '-inf', '+inf')
            if not srv.startswith('<empty')
               and srv not in cfgbysrv]

def configs_start_with_newline(cfgbysrv):
    """At some point we've found configurations that don't start with a newline.
    These will pass fallback checks, but they won't merge nicely into the config
    passed to users. Here we check against that."""
    return ["Server %s's config doesn't start with a newline" % srv
            for srv, cfg in cfgbysrv.iteritems()
            if not cfg.startswith("\n")]

def all_fps_have_pillar():
    pillars = os.listdir('/srv/pillar')
    return ["Fallback %s doesn't have an associated pillar" % name
            for dc in ['vltok1', 'doams3']
            for name in redis_shell.lrange(dc + ':vpss', 0, -1)
            if (name.startswith('fp-nl-') or name.startswith('fp-jp-'))
               and name + '.sls' not in pillars]

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
           + srvs_in_cfgbysrv('doams3', cfgbysrv)
           + all_fps_have_pillar())


if __name__ == '__main__':
    run_all_checks()
