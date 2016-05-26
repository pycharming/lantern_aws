#!/usr/bin/env python


from alert import alert
from redis_util import redis_shell


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
    alert(type='sanity-check-failures',
          details={'errors': errors},
          text='\n'.join(errors),
          color='danger')

def run_all_checks():
    srv2cfg = redis_shell.hgetall('srv->cfg')
    errors = configs_start_with_newline(srv2cfg)
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
