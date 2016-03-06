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
    srvid = redis_shell.hget('srvip->srv', ip)
    skey = region + ":slices"
    score = redis_shell.zscore(skey, srvid)
    if not score:
        print "I was not open, so I won't try to close myself."
        flag_as_done(close_flag_filename)
        return
    p = redis_shell.pipeline()
    p.zrem(skey, srvid)
    p.zadd(skey, ('<empty:%s>' % score), score)
    p.execute()
    flag_as_done(close_flag_filename)
    # Save the slice I had assigned; it might be useful for debugging and for
    # responding to server overload in this slice.
    file('slice', 'w').write(str(score))
    alert(type='proxy-closed',
          details={'reason': msg},
          text="*Closed* because I " + msg,
          color='good')

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
