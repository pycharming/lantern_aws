"""Cache time-consuming queries for convenience when developing or playing with the REPL."""

import misc_util
from redis_util import redis_shell
import vps_util


@misc_util.memoized
def srv_cfg_by_ip():
    print "Fetching config data..."
    ret = vps_util.srv_cfg_by_ip()
    print "...done fetching config data."
    print
    return ret

@misc_util.memoized
def all_vpss(provider):
    print "Fetching VPS list for provider '%s'..." % provider
    ret = vps_util.vps_shell(provider).all_vpss()
    print "...done fetching VPS list for provider '%s'." % provider
    print
    return ret

@misc_util.memoized
def requests(which, country):
    print "Fetching %s requests for country '%s'..." % (which, country)
    ret = redis_shell.hgetall("%s:%s-requests" % (country, which))
    print "...done fetching %s requests." % which
    print
    ret = {k: int(v) for k, v in ret.iteritems()}
    return ret

@misc_util.memoized
def srv2region(srv):
    return redis_shell.hget('srv->user-region', srv)
