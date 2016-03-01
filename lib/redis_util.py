from collections import namedtuple
from datetime import datetime
import os
from StringIO import StringIO

import redis

# pip install python-dateutil
from dateutil.tz import tzutc
# pip install --use-wheel --pre transit-python
from transit.reader import Reader
from transit.writer import Writer


redis_shell = redis.from_url(os.getenv('REDIS_URL'))

logkey = 'log'
# We keep a sliding buffer of logs of this length. Length is a bit generous now
# because we haven't implemented consumers yet.
max_history_length = 100000


def utcnow():
    "A timezone-aware (as required by transit) datetime for now in UTC."
    return datetime.now(tzutc())

def log2redis(data, pipeline=None, db_version=None):
    msg = {'time': utcnow(),
           'data': data}
    if db_version:
        msg['db_version': db_version]
    io = StringIO()
    Writer(io, 'json').write(msg)
    s = io.getvalue()
    if redis_shell.llen(logkey) >= max_history_length:
        p = pipeline or redis_shell.pipeline()
        p.lpop(logkey)
    else:
        p = pipeline or redis_shell
    p.rpush(logkey, s)
    if p not in [pipeline, redis_shell]:
        p.execute()

def read_log_entry(s):
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
