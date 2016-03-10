from contextlib import contextmanager
from datetime import datetime
import itertools as it
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
import misc_util as util


pillar_tmpl = """\
controller: lanternctrl1-2
auth_token: %s
install-from: git
instance_id: %s
proxy_protocol: tcp
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

def save_pillar(name):
    with file("/srv/pillar/%s.sls" % name, 'w') as f:
        f.write(pillar_tmpl % (random_auth_token(), name))

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
def hammer_the_damn_thing_until_it_proxies(name, ssh_tmpl, fetchaccessdata_cmd):
    reboot_cmd = ssh_tmpl % 'reboot'
    kill_tmpl = ssh_tmpl % 'kill -9 %s'
    with tempdir(name):
        while True:
            print("Rebooting...")
            trycmd(reboot_cmd)
            time.sleep(10)
            print("Fetching access data...")
            if trycmd(fetchaccessdata_cmd, 5):
                access_data = file('access_data.json').read()
                file('fallbacks.json', 'w').write("[" + access_data + "]")
                for tries in xrange(3):
                    out = subprocess.check_output(['checkfallbacks',
                                                   '-fallbacks', 'fallbacks.json',
                                                   '-connections', '1'])
                    if "[failed fallback check]" in out:
                        print("Fallback check failed; retrying...")
                    else:
                        print("VPS up!")
                        return yaml.load(access_data)
                    time.sleep(10)
            print("Minion seems to be misconfigured.  Let's try reapplying salt state...")
            pid = highstate_pid(name)
            if pid:
                trycmd(kill_tmpl % pid, 5)
            # Sometimes our hammering interrupts dpkg such that highstate will
            # always fail to install any apt packages.
            trycmd("salt %s cmd.run 'dpkg --configure -a'" % name)
            trycmd("salt -t 1200 %s state.highstate" % name)

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

def actually_retire_proxy(name, ip, pipeline=None):
    """
    While retire_proxy just enqueues the proxy for retirement, this actually
    updates the redis tables.
    """
    name, ip, srv = nameipsrv(name=name, ip=ip)
    cm = cm_by_name(name)
    region = region_by_name(name)
    txn = pipeline or redis_shell.pipeline()
    if srv:
        actually_close_proxy(name, ip, srv, txn)
        txn.hdel('srv->cfg', srv)
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
    else:
        assert False, repr(provider_etc)

def destroy_vps(name):
    vps_shell(dc_by_name(name)).destroy_vps(name)

def todaystr():
    now = datetime.utcnow()
    return "%d%02d%02d" % (now.year, now.month, now.day)

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

    return name.split('-')[1]

def region_by_name(name):
    return region_by_dc(dc_by_name(name))

def my_region():
    return region_by_dc(dc_by_cm(my_cm()))

def dc_by_cm(cm):
    ret = cm[:6]
    assert ret in _region_by_production_cm
    return ret

_region_by_production_cm = {'doams3': 'etc',
                            'vlfra1': 'etc',
                            'dosgp1': 'sea',
                            'vltok1': 'sea'}
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

    def __init__(self, name, ip, ram, provider, etc):
        self.name = name
        self.ip = ip
        self.ram = ram
        self.provider = provider
        self.etc = etc

    def __repr__(self):
        return "<%s (%s)>" % (self.name, self.ip)

def all_vpss():
    return (set(vps_shell('vl').all_vpss())
            | set(vps_shell('do').all_vpss()))

def retire_proxy(name=None, ip=None, srv=None, reason='failed checkfallbacks', pipeline=None):
    name, ip, srv = nameipsrv(name, ip, srv)
    region = region_by_name(name)
    if srv == redis_shell.get(region + ':fallbacksrv'):
        print >> sys.stderr, "I'm *not retiring* %s (%s) because it is the fallback server for region '%s'." % (name, ip, region)
        print >> sys.stderr, "Please set a new fallback server first."
        return
    p = pipeline or redis_shell.pipeline()
    p.rpush(cm_by_name(name) + ':retireq', '%s|%s' % (name, ip))
    log2redis({'op': 'retire',
               'name': name,
               'ip': ip,
               'srv': srv,
               'reason': reason},
              pipeline=p)
    if not pipeline:
        p.execute()

def pull_from_srvq(region):
    import fetchcfg
    srv = redis_shell.incr('srvcount')
    ip, name, cfg = fetchcfg.fetch(region)
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
