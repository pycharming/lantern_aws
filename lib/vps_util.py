from contextlib import contextmanager
from datetime import datetime
import itertools as it
import json
import os
import random
import re
import subprocess
import string
import sys
import tempfile
import time

import yaml

import redis_util
from redis_util import log2redis, nameipsrv, redis_shell


pillar_tmpl = """\
controller: lanternctrl1-2
auth_token: %s
install-from: git
instance_id: %s
proxy_protocol: tcp
obfs4_port: %s
"""

auth_token_alphabet = string.ascii_letters + string.digits
auth_token_length = 64

highstate_re = re.compile(r'The function "state.highstate" is running as PID (\d+)')

@contextmanager
def tempdir(id_):
    olddir = os.getcwd()
    workdir = tempfile.mkdtemp(prefix='init_vps_%s_' % id_)
    os.chdir(workdir)
    try:
        yield
    finally:
        os.chdir(olddir)
        os.system("rm -rf " + workdir)

def random_auth_token():
    return ''.join(random.choice(auth_token_alphabet)
                   for _ in xrange(auth_token_length))

def save_pillar(name, req):
    obfs4_port = req.get('obfs4_port', 0)
    with file("/srv/pillar/%s.sls" % name, 'w') as f:
        f.write(pillar_tmpl % (random_auth_token(), name, obfs4_port))

def trycmd(cmd, tries=sys.maxsize):
    for x in xrange(tries):
        if not os.system(cmd):
            return True
        print("Command failed; retrying: %s" % cmd)
        time.sleep(10)
    return False

def highstate_pid(name):
    out = subprocess.check_output(["salt", name, "state.running"])
    lines = out.strip().split('\n')
    if len(lines) > 1:
        match = highstate_re.search(lines[1])
        if match:
            return match.groups()[0]
    return None

# For good measure.
def hammer_the_damn_thing_until_it_proxies(name):
    def saltcmd(cmd):
        return "salt %s cmd.run '%s'" % (name, cmd)
    def trysaltcmd(cmd):
        return trycmd(saltcmd(cmd), 5)
    with tempdir(name):
        while True:
            print("Rebooting...")
            trysaltcmd('reboot')
            for _ in xrange(10):
                time.sleep(10)
                print("Fetching access data...")
                try:
                    adstr = subprocess.check_output(['salt', name, 'cmd.run', 'cat /home/lantern/access_data.json'])
                except subprocess.CalledProcessError as e:
                    print "Error %s fetching access data" % e.returncode
                    print "Output was:"
                    print e.output
                    continue
                if adstr:
                    # Remove header line
                    adstr = adstr.split('\n', 1)[1]
                if adstr and not adstr.strip().startswith('Minion did not return.'):
                    file('fallbacks.json', 'w').write("[" + adstr + "]")
                    for tries in xrange(3):
                        out = subprocess.check_output(['checkfallbacks',
                                                       '-fallbacks', 'fallbacks.json',
                                                       '-connections', '1'])
                        if "[failed fallback check]" in out:
                            print("Fallback check failed; retrying...")
                        else:
                            print("VPS up!")
                            return json.loads(adstr)
                        time.sleep(10)
            print("Minion seems to be misconfigured.  Let's try reapplying salt state...")
            pid = highstate_pid(name)
            if pid:
                trysaltcmd("kill -9 %s" % pid)
            # Sometimes our hammering interrupts dpkg such that highstate will
            # always fail to install any apt packages. This dpkg command takes
            # us out of that lock.
            trysaltcmd("dpkg --configure -a")
            trycmd("salt -t 1200 %s state.highstate" % name, 1)

def cleanup_keys(do_shell=None, vultr_shell=None):
    vpss = all_vpss()
    ignore = set(["Accepted", "Unaccepted", "Rejected", "Keys:"])
    filter_out = vpss | ignore
    for key in subprocess.check_output(['salt-key', '-L']).split():
        if key not in filter_out:
            os.system('salt-key -d ' + key)

def srv_cfg_by_ip():
    ret = {}
    for srv, cfg in redis_shell.hgetall('srv->cfg').iteritems():
        ip = yaml.load(cfg).values()[0]['addr'].split(':')[0]
        if ip in ret:
            ret[ip][1].append(srv)
        else:
            ret[ip] = cfg, [srv]
    return ret

def actually_close_proxy(name=None, ip=None, srv=None, pipeline=None):
    name, ip, srv = nameipsrv(name, ip, srv)
    region = region_by_name(name)
    slices_key = region + ':slices'
    def remove_if_there(k):
        score = redis_shell.zscore(slices_key, k)
        if score is None:
            return False
        else:
            txn.zrem(slices_key, k)
            txn.zadd(slices_key, "<empty:%s>" % int(score), score)
            return True
    txn = pipeline or redis_shell.pipeline()
    remove_if_there(srv)
    c = it.count()
    while remove_if_there('%s|%s' % (srv, c.next())):
        pass
    if txn is not pipeline:
        txn.execute()

class ProxyGone(Exception):
    def __init__(self, name, ip, srv):
        self.name = name
        self.ip = ip
        self.srv = srv

def actually_offload_proxy(name=None, ip=None, srv=None, pipeline=None):
    name, ip, srv = nameipsrv(name, ip, srv)
    if srv is None:
        raise ProxyGone(name, ip, srv)
    region = region_by_name(name)
    client_table_key = region + ':clientip->srv'
    packed_srv = redis_util.pack_srv(srv)
    #XXX: a proxy -> {clients} index is sorely needed!
    # Getting the set of clients assigned to this proxy takes a long time
    # currently.  Let's get it done before pulling the replacement proxy,
    # so we're less likely to be left with an empty proxy if interrupted.
    clients = set(pip
                  for pip, psrv in redis_shell.hgetall(client_table_key).iteritems()
                  if psrv == packed_srv)
    dest = pull_from_srvq(region)
    # It's still possible that we'll crash or get rebooted here, so the
    # destination server will be left empty. The next closed proxy compaction
    # job will find this proxy and assign some users to it or mark it for
    # retirement.
    dest_psrv = redis_util.pack_srv(dest.srv)
    redis_shell.hmset(client_table_key, {pip: dest_psrv for pip in clients})
    print "Offloaded clients from %s (%s) to %s (%s)" % (name, ip, dest.name, dest.ip)

def actually_retire_proxy(name, ip, srv=None, pipeline=None):
    """
    While retire_proxy just enqueues the proxy for retirement, this actually
    updates the redis tables.
    """
    name, ip, srv = nameipsrv(name=name, ip=ip, srv=srv)
    cm = cm_by_name(name)
    region = region_by_name(name)
    txn = pipeline or redis_shell.pipeline()
    if srv:
        actually_close_proxy(name, ip, srv, txn)
        txn.hdel('srv->cfg', srv)
        txn.hdel('server->config', name)
        txn.hdel('srv->name', srv)
        txn.hdel('srv->srvip', srv)
        txn.hdel('name->srv', name)
        txn.hdel('srvip->srv', ip)
        # For debugging purposes; we can delete these anytime if they're a
        # space problem.
        txn.hset('history:srv->name', srv, name)
        txn.hset('history:name->srv', name, srv)
        txn.hset('history:srv->srvip', srv, ip)
        # An IP may be used by multiple servers through history.
        txn.rpush('history:srvip->srv:%s' % ip, srv)
        txn.incr('srvcount')
    else:
        print "No configs left to delete for %s." % name
    # Check whether this server is in the queue (because of recycling).
    for cfg in redis_shell.lrange(region + ':srvq', 0, -1):
        if cfg.split('|')[0] == ip:
            txn.lrem(region + ':srvq', cfg)
    txn.lrem(cm + ':vpss', name)
    txn.incr(cm + ':vpss:version')
    if txn is not pipeline:
        txn.execute()

def vps_shell(provider_etc):
    """
    provider_etc is any string that starts with the provider ID.

    By convention, datacenter and cloudmaster IDs meet this condition.
    """
    if provider_etc.startswith('do'):
        import do_util
        return do_util
    elif provider_etc.startswith('vl'):
        import vultr_util
        return vultr_util
    elif provider_etc.startswith('li'):
        import linode_util
        return linode_util
    else:
        assert False, repr(provider_etc)

def destroy_vps(name):
    vps_shell(dc_by_name(name)).destroy_vps(name)

def todaystr():
    now = datetime.utcnow()
    return "%d%02d%02d" % (now.year, now.month, now.day)

def new_vps_serial(prefix, cm=None, datestr=None):
    if cm is None:
        cm = my_cm()
    if datestr is None:
        datestr = todaystr()
    key = 'serial:%s:%s:%s' % (cm, prefix, datestr)
    p = redis_shell.pipeline()
    p.incr(key)
    p.expire(key, 25 * 60 * 60)
    return p.execute()[0]

def new_vps_name(prefix):
    date = todaystr()
    cm = my_cm()
    return "-".join([prefix, cm, date, str(new_vps_serial(prefix, cm, date)).zfill(3)])

def my_cm():
    """
    The name of the cloudmaster managing me, excluding the 'cm-' prefix.
    """
    return os.getenv('CM')[3:]  # remove the "cm-" prefix

def cm_by_name(name):

    # Legacy.
    if name.startswith('fp-nl-'):
        name = name.replace('nl', 'doams3', 1)
    elif name.startswith('fp-jp-'):
        name = name.replace('jp', 'vltok1', 1)

    # We need to count from the right because we have HTTPS proxies both with
    # and without the -https- part in their name.
    return name.split('-')[-3]

def region_by_name(name):
    return region_by_dc(dc_by_name(name))

def my_region():
    return region_by_dc(dc_by_cm(my_cm()))

def dc_by_cm(cm):
    ret = cm[:6]
    assert ret in _region_by_production_cm
    return ret

_region_by_production_cm = {'donyc3': 'etc',
                            'doams3': 'ir',
                            # The vlfra1 and vlpar1 cloudmasters are no more,
                            # but if we were to bring them back, it would be in
                            # this region.
                            'vlfra1': 'ir',
                            'vlpar1': 'ir',
                            'dosgp1': 'sea',
                            'dosfo1': 'sea',
                            'vltok1': 'sea',
                            'lisgp1': 'sea',
                            'litok1': 'sea',
                            'vllan1': 'etc'}
def region_by_dc(dc):
    return _region_by_production_cm[dc]

def dc_by_name(name):
    return dc_by_cm(cm_by_name(name))

def access_data_to_cfg(access_data):
    ret = access_data.copy()
    ip = ret['addr'].split(':')[0]
    ret.update(pipeline=True,
               trusted=True,
               qos=10,
               weight=1000000)
    return "\n    " + yaml.dump({'fallback-' + ip: ret})

class vps:

    def __init__(self, name, ip, ram, provider, provider_url, etc):
        self.name = name
        self.ip = ip
        self.ram = ram
        self.provider = provider
        self.provider_url = provider_url
        self.dashboard_url = "https://dashboard.getlantern.org/dashboard/script/single-proxy.js?name=%s" % name
        self.etc = etc

    def browse(self):
        for url in [self.dashboard_url, self.provider_url]:
            os.system('google-chrome-stable --new-tab %s > /dev/null 2>&1 &' % url)

    def __repr__(self):
        return "<%s (%s)>" % (self.name, self.ip)

def all_vpss():
    return (set(vps_shell('vl').all_vpss())
            | set(vps_shell('do').all_vpss())
            | set(vps_shell('li').all_vpss()))

def proxy_status(name=None, ip=None, srv=None):
    name, _, srv = nameipsrv(name, ip, srv)
    if srv is None:
        if name is not None:
            region = region_by_name(name)
            for qentry in redis_shell.lrange(region + ':srvq', 0, -1):
                if qentry.split('|')[1] == name:
                    return 'enqueued'
        return 'baked-in'
    elif redis_shell.zscore(region_by_name(name) + ':slices', srv) is None:
        return 'closed'
    else:
        return 'open'

def offload_if_closed(name=None, ip=None, srv=None, reason='failed_checkfallbacks', pipeline=None):
    retire_proxy(name, ip, srv, reason, pipeline, proxy_status(name, ip, srv) == 'closed')

def retire_proxy(name=None, ip=None, srv=None, reason='failed checkfallbacks', pipeline=None, offload=False):
    name, ip, srv = nameipsrv(name, ip, srv)
    region = region_by_name(name)
    if redis_shell.sismember(region + ':fallbacks', srv):
        print >> sys.stderr, "I'm *not retiring* %s (%s) because it is a fallback server for region '%s'." % (name, ip, region)
        print >> sys.stderr, "Please remove it as a fallback first."
        return
    if redis_shell.sismember(region + ':honeypots', srv):
        print >> sys.stderr, "I'm *not retiring* %s (%s) because it is a honeypot server for region '%s'." % (name, ip, region)
        print >> sys.stderr, "Please remove it as a honeypot first."
        return
    p = pipeline or redis_shell.pipeline()
    if offload:
        qname = '%s:offloadq' % region_by_name(name)
    else:
        qname = '%s:retireq' % cm_by_name(name)
    p.rpush(qname, '%s|%s' % (name, ip))
    log2redis({'op': 'retire',
               'name': name,
               'ip': ip,
               'srv': srv,
               'reason': reason},
              pipeline=p)
    if not pipeline:
        p.execute()

def pull_from_srvq(prefix, refill=True):
    x = redis_shell.rpop(prefix + ':srvq')
    if x is None:
        raise RuntimeError("No servers to pull from the %s queue" % prefix)
    ip, name, cfg = x.split('|')
    srv = redis_shell.incr('srvcount')
    p = redis_shell.pipeline()
    if refill:
        p.lpush(prefix + ':srvreqq', srv)
    p.hset('server->config', name, cfg)
    p.hset('srv->cfg', srv, cfg)
    p.hset('srv->name', srv, name)
    p.hset('name->srv', name, srv)
    p.hset('srvip->srv', ip, srv)
    p.hset('srv->srvip', srv, ip)
    p.execute()
    return redis_util.nis(name, ip, srv)

def assign_clientip_to_srv(clientip, srvname=None, srvip=None, srv=None):
    nis = redis_util.nameipsrv(srvname, srvip, srv)
    region = region_by_name(nis.name)
    redis_shell.hset(region + ':clientip->srv',
                     redis_util.pack_ip(clientip),
                     redis_util.pack_srv(nis.srv))

def assign_clientip_to_new_own_srv(clientip, region):
    name, ip, srv = pull_from_srvq(region)
    assign_clientip_to_srv(clientip, name, ip, srv)
    return name, ip, srv

def is_production_proxy(name):
    return name.startswith('fp-') and cm_by_name(name) in _region_by_production_cm

def serialize_access_data(access_data, name):
    ad = access_data.copy()
    # DRY: flashlight/genconfig/cloud.yaml.tmpl
    ad.update(pipeline=True,
              trusted=True,
              qos=10,
              weight=1000000)
    # Use safe_dump to avoid `!!python/unicode` markers for unicode strings.
    return "\n    " + yaml.safe_dump({name: ad})

def enqueue_cfg(name, access_data, srvq):
    "Upload a config to a server queue."
    ip = access_data['addr'].split(':')[0]
    cfg = serialize_access_data(access_data, name)
    txn = redis_shell.pipeline()
    txn.hset('server->config', name, cfg)
    txn.lpush(srvq, "%s|%s|%s" % (ip, name, cfg))
    txn.execute()

def fix_cert_newlines(d):
    d = d.copy()
    d['cert'] = re.sub(r'[\r\n\\]+', '\n', d['cert'])
    return d

def fix_access_data(qentry, fixfn):
    ip, name, cfg = qentry.split('|')
    access_data = yaml.load(cfg).values()[0]
    fixed_access_data = fixfn(access_data)
    return '|'.join([ip, name, serialize_access_data(fixed_access_data, name)])

def filter_queue(qname, fn):
    bakname = qname + '.bak'
    redis_shell.rename(qname, bakname)
    p = redis_shell.pipeline()
    for entry in redis_shell.lrange(bakname, 0, -1):
        p.lpush(qname, fn(entry))
    p.execute()

def fix_queues():
    regions = redis_shell.smembers('user-regions')
    cloudmasters = redis_shell.smembers('cloudmasters')
    for domain in regions | cloudmasters:
        qname = domain + ':srvq'
        if redis_shell.exists(qname):
            print "fixing queue for %s..." % domain
            fix_queue(qname)
        else:
            print "no queue for %s." % domain

# Ad hoc application of the building blocks above. Leaving them around, should
# they serve as inspiration for future fixing jobs.

def fix_queue(qname):
    filter_queue(qname, lambda s: fix_access_data(s, fix_cert_newlines))

def fix_live_servers():
    srv2cfg = redis_shell.hgetall('srv->cfg')
    fixed = {}
    for srv, cfg in srv2cfg.iteritems():
        if '\\' in cfg:
            name, access_data = yaml.load(cfg).items()[0]
            print "fixing srv %s..." % name
            fixed_access_data = fix_cert_newlines(access_data)
            fixed_cfg = serialize_access_data(fixed_access_data, name)
            fixed[srv] = fixed_cfg
    redis_shell.hmset('srv->cfg', fixed)

def destroy_until_dc(srvq, dc):
    """
    Pop proxies off the server queue, retire them and destroy them, until we
    hit one with the desired DC.

    This is used when we want to quickly start serving a user region from a
    specific datacenter.
    """
    while True:
        entry = redis_shell.rpop(srvq)
        ip, name, cfg = entry.split('|')
        print "popping", name
        next_dc = dc_by_name(name)
        if next_dc == dc:
            print "pushing back", name
            redis_shell.rpush(srvq, entry)
            return
        retire_proxy(name=name, ip=ip, reason="Flushing server queue")
