from collections import namedtuple
from datetime import datetime
import os
import here
from StringIO import StringIO

import redis

# pip install python-dateutil
from dateutil.tz import tzutc
# pip install --use-wheel --pre transit-python
from transit.reader import Reader
from transit.writer import Writer

redis_url = os.getenv('REDIS_URL')
redis_args = dict()
if redis_url.startswith("rediss"):
    # TLS connection
    redis_args["ssl_ca_certs"] = os.path.join(here.secrets_path,
                                              'redis',
                                              'garantia_ca.pem')

    redis_args["ssl_keyfile"] = os.path.join(here.secrets_path,
                                             'redis',
                                             'garantia_user_private.key')

    redis_args["ssl_certfile"] = os.path.join(here.secrets_path,
                                              'redis',
                                              'garantia_user.crt')

redis_shell = redis.from_url(os.getenv('REDIS_URL'), **redis_args)

logkey = 'log'
versionkey = 'version'
# We keep a sliding buffer of logs of this length. Length is a bit generous now
# because we haven't implemented consumers yet.
max_history_length = 100000


def utcnow():
    "A timezone-aware (as required by transit) datetime for now in UTC."
    return datetime.now(tzutc())

def log2redis(data, pipeline=None, time=None):
    """
    Log an event or mutation to the general redis log.

    For a mutating operation, call this with the pipeline where your changes
    are performed. Also call `bump_version` *once* with that pipeline, *before*
    any calls to this.

    The UTC date/time and DB version of the database at the time of logging
    (that is, prior to any bumping) are recorded in the log.
    """
    time = time or utcnow()
    version = redis_shell.get(versionkey) or 0
    msg = {'time': time,
           'version': version,
           'data': data}
    s = transit_dumps(msg)
    if redis_shell.llen(logkey) >= max_history_length:
        # We only create a new pipeline here if we are to discard old logs, so
        # we at least keep the log size constant. We don't watch for the length
        # of the log because the limit is meant to be approximate anyway.
        p = pipeline or redis_shell.pipeline()
        p.lpop(logkey)
    else:
        p = pipeline or redis_shell
    p.rpush(logkey, s)
    if p not in [pipeline, redis_shell]:
        p.execute()

def bump_version(p):
    """
    For a mutating operation, call this with the pipeline where your mutations
    are performed. Then be ready to catch redis.WatchError when you execute the
    pipeline.

    [1] https://github.com/andymccurdy/redis-py#pipelines
    """
    p.watch(versionkey)
    p.incr(versionkey)
    p.multi()

def transit_dumps(x):
    io = StringIO()
    Writer(io, 'json').write(x)
    return io.getvalue()

def transit_loads(s):
    return Reader('json').read(StringIO(s))

nis = namedtuple('nameipsrv', ['name', 'ip', 'srv'])

def nameipsrv(name=None, ip=None, srv=None):
    if not name and not ip and not srv:
        raise ValueError('need srv, name or ip')
    if not name:
        if not srv:
            srv = redis_shell.hget('srvip->srv', ip)
        name = redis_shell.hget('srv->name', srv)
    if not ip:
        if not srv:
            srv = redis_shell.hget('name->srv', name)
        ip = redis_shell.hget('srv->srvip', srv)
    if not srv:
        srv = redis_shell.hget('name->srv', name)
    return nis(name, ip, srv)

def namesipssrvs(names=None, ips=None, srvs=None):
    if len(filter(None, [names, ips, srvs])) != 1:
        raise ValueError('Currently only one input list is supported.')
    if not names:
        if not srvs:
            srvs = redis_shell.hmget('srvip->srv', *ips)
        names = redis_shell.hmget('srv->name', *srvs)
    if not ips:
        if not srvs:
            srvs = redis_shell.hmget('name->srv', *names)
        ips = redis_shell.hmget('srv->srvip', *srvs)
    if not srvs:
        srvs = redis_shell.hmget('name->srv', *names)
    return map(nis, names, ips, srvs)

def pack_ip(ip):
    return ''.join(chr(int(c)) for c in ip.split('.'))

def pack_srv(srv):
    #XXX: make robust for srv > 2 ** 16
    srv = int(srv)
    return chr(srv // 256) + chr(srv % 256)

def unpack2int(s):
    ret =  sum(ord(c) << (8 * i)
               for i, c in enumerate(reversed(s)))
    # special case: encoded IPv6 addresses
    if len(s) == 7 and ret > 2 ** 55:
        ret -= 2 ** 56
    return ret
