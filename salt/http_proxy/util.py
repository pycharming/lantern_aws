import datetime
import json
import os

from alert import alert, send_to_slack
from redis_util import redis_shell
import vps_util

auth_token = "{{ pillar['cfgsrv_token'] }}"
instance_id = "{{ grains['id'] }}"
region = vps_util.region_by_name(instance_id)

# {% from 'ip.sls' import external_ip %}
ip = "{{ external_ip(grains) }}"
last_offload_filename = "server_last_offloaded"
close_flag_filename = "server_closed"
retire_flag_filename = "server_retired"

# Once we offload a proxy, we allow this many seconds for the proxy to cool
# down before allowing it to offload itself again.
offload_timeout = 4 * 60 * 60


def flag_as_done(flag_filename):
    file(flag_filename, 'w').write(str(datetime.datetime.utcnow()))

def am_I_closed():
    srv = redis_shell.hget('name->srv', instance_id)
    if srv is None:
        print "I'm retired or a baked in proxy"
        return False
    if redis_shell.zscore(region + ':slices', srv) is not None:
        print "I'm open"
        return False
    print "I'm closed"
    return True

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

def _reset_last_offload():
    json.dump(time.time(), file(last_offload_filename, 'w'))

def _offloaded_recently():
    try:
        t = json.load(file(last_offload_filename))
    except IOError:
        return False
    return time.time() - t < offload_timeout

def _actually_offload(proportion, replace, name, ip):
    "Bypasses offload timeout and slack logging."
    _reset_last_offload()
    vps_util.offload_proxy(proportion=proportion,
                           replace=replace,
                           name=name,
                           ip=ip)

def offload_server(msg, proportion, replace):
    if not _offloaded_recently():
        send_to_slack(title="Proxy offloading",
                      text="*Offloading* because I " + msg,
                      color='good')
        _actually_offload(proportion, replace, instance_id, ip)

def retire_server(msg, offload=False):
    if os.path.exists(retire_flag_filename):
        print "Not retiring myself again."
        return
    if offload:
        _actually_offload(proportion=1.0, replace=True, name=instance_id, ip=ip)
    vps_util.retire_proxy(name=instance_id, ip=ip, reason=msg, offload=offload)
    flag_as_done(retire_flag_filename)
    if offload:
        offloaded = "*Offloading* and "
    else:
        offloaded = ""
    send_to_slack(title="Proxy retiring",
                  text=offloaded + "*Retiring* because I " + msg,
                  color='good')
