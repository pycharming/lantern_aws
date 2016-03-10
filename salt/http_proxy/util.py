import datetime
import os

from alert import alert
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

def close_server(msg):
    if os.path.exists(close_flag_filename):
        print "Not closing myself again."
        return
    txn = redis_shell.pipeline()
    actually_close_proxy(name=instance_id, ip=ip, pipeline=txn)
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
    redis_shell.lpush(vps_util.my_cm() + ':retireq', '%s|%s' % (instance_id, ip))
    flag_as_done(retire_flag_filename)
    alert(type='proxy-retired',
          details={'reason': msg},
          text="*Retired* because I " + msg,
          color='warning')
