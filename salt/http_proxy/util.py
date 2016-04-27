import datetime
import os

from alert import alert, send_to_slack
from redis_util import redis_shell, pack_srv
import vps_util

auth_token = "{{ pillar['cfgsrv_token'] }}"
instance_id = "{{ grains['id'] }}"
region = vps_util.region_by_name(instance_id)

# {% from 'ip.sls' import external_ip %}
ip = "{{ external_ip(grains) }}"
close_flag_filename = "server_closed"
retire_flag_filename = "server_retired"


def flag_as_done(flag_filename):
    file(flag_filename, 'w').write(str(datetime.datetime.utcnow()))

def offload_if_closed():
    # XXX: assumes that users will fit in the replacement server.
    # As of this writing, while there are some 1GB Vultr proxies, their load
    # should fit in a 768MB one, because that's what closed proxy compaction
    # jobs normalize for.
    # There are also some dedicated proxies serving way too many users for a
    # 768MB one, but I'll offload and retire these manually.
    srv = redis_shell.hget('name->srv', instance_id)
    if srv is None:
        print "I'm retired or a baked in proxy; I can't offload myself."
        return
    if redis_shell.zscore(region + ':slices', srv) is not None:
        print "I'm open, so no point in offloading myself"
        return
    print "Offloading clients before retiring myself..."
    packed_srv = pack_srv(srv)
    client_table_key = region + ':clientip->srv'
    #XXX: a reverse index is sorely needed!
    # Getting the set of clients assigned to this proxy takes a long time
    # currently.  Let's get it done before pulling the replacement server,
    # so we're less likely to be left with an empty server.
    clients = set(pip
                  for pip, psrv in redis_shell.hgetall(client_table_key).iteritems()
                  if psrv == packed_srv)
    dest = vps_util.pull_from_srvq(region)
    # It's still possible that we'll crash or get rebooted here, so the
    # destination server will be left empty. The next closed proxy compaction
    # job will find this proxy and assign some users to it or mark it for
    # retirement.
    dest_psrv = pack_srv(dest.srv)
    redis_shell.hmset(client_table_key, {pip: dest_psrv for pip in clients})
    print "Offloaded clients to %s (%s)" % (dest.name, dest.ip)

def close_server(msg):
    if os.path.exists(close_flag_filename):
        print "Not closing myself again."
        return
    txn = redis_shell.pipeline()
    vps_util.actually_close_proxy(name=instance_id, ip=ip, pipeline=txn)
    alert(type='proxy-closed',
          details={'reason': msg},
          text="*Closed* because I " + msg,
          color='good',
          pipeline=txn)
    txn.execute()
    flag_as_done(close_flag_filename)

def retire_server(msg):
    if os.path.exists(retire_flag_filename):
        print "Not retiring myself again."
        return
    vps_util.retire_proxy(name=instance_id, ip=ip, reason=msg)
    flag_as_done(retire_flag_filename)
    send_to_slack(title="Proxy retired",
                  text="*Retired* because I " + msg,
                  color='warning')
