import datetime
import os

from alert import alert, send_to_slack
from redis_util import redis_shell
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

def retire_server(msg, offload=False):
    if os.path.exists(retire_flag_filename):
        print "Not retiring myself again."
        return
    vps_util.retire_proxy(name=instance_id, ip=ip, reason=msg, offload=offload)
    flag_as_done(retire_flag_filename)
    if offload:
        offloaded = "*Offloading* and "
    else:
        offloaded = ""
    send_to_slack(title="Proxy retiring",
                  text=offloaded + "*Retiring* because I " + msg,
                  color='good')
