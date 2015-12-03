#!/usr/bin/env python


import multiprocessing
from Queue import Empty
import os
import time
import traceback

import yaml

from redis_util import redis_shell
import redisq
import vps_util


CM = vps_util.my_cm()
REGION = vps_util.my_region()
MAXPROCS = int(os.getenv('MAXPROCS'))
LAUNCH_TIMEOUT = 60 * 60

vps_shell = vps_util.vps_shell(CM)


def run():
    print "Serving user region", repr(REGION), ", MAXPROCS:", repr(MAXPROCS)
    qname = REGION + ":srvreqq"
    reqq = redisq.Queue(qname, redis_shell, LAUNCH_TIMEOUT)
    procq = multiprocessing.Queue()
    pending = {}
    def kill_task(reqid):
        print "Killing timed out process and vps..."
        task = pending.pop(reqid)
        task['proc'].terminate()
        proc = multiprocessing.Process(target=vps_shell.destroy_vps,
                                       args=(task['name'],))
        proc.daemon = True
        proc.start()
    while True:
        while not procq.empty():
            try:
                result = procq.get(False)
                print "Got result:", result
                task = pending.get(result['reqid'])
                if task and task['name'] == result['name']:
                    del pending[result['reqid']]
                    upload_cfg(result['name'], result['access_data'])
                    register_vps(task['name'])
                    task['remove_req']()
            except Empty:
                print "Wat?"
                break
        if len(pending) < MAXPROCS:
            reqid, remover = reqq.next_job()
            if reqid:
                print "Got request", reqid
                if reqid in pending:
                    print "Killing task %s because of queue timeout" % reqid
                    kill_task(reqid)
                name = get_lcs_name()
                proc = multiprocessing.Process(target=launch_one_server,
                                               args=(procq,
                                                     reqid,
                                                     name))
                proc.daemon = True
                pending[reqid] = {
                    'name': name,
                    'proc': proc,
                    'starttime': time.time(),
                    'remove_req': remover}
                print "Starting process to launch", name
                proc.start()
        else:
            # Since we're not checking the queue when we've maxed out our
            # processes, we need to manually check for expired tasks.
            for reqid, d in pending.items():
                if time.time() - d['starttime'] > LAUNCH_TIMEOUT:
                    print "Killing task %s because of local timeout" % reqid
                    kill_task(reqid)
        time.sleep(10)

def get_lcs_name():
    date = vps_util.todaystr()
    if redis_shell.get(CM + ':lcsserial:date') == date:
        serial = redis_shell.incr(CM + ':lcsserial')
    else:
        pipe = redis_shell.pipeline()
        pipe.set(CM + ':lcsserial:date', date)
        pipe.set(CM + ':lcsserial', 1)
        pipe.execute()
        serial = 1
    return 'fp-%s-%s-%03d' % (CM, date, serial)

def launch_one_server(q, reqid, name):
    q.put({'reqid': reqid,
           'name': name,
           'access_data': vps_shell.init_vps(vps_shell.create_vps(name))})

def upload_cfg(name, access_data):
    ip = access_data['addr'].split(':')[0]
    # DRY: flashlight/genconfig/cloud.yaml.tmpl
    access_data.update(pipeline=True,
                       trusted=True,
                       qos=10,
                       weight=1000000)
    cfg = "\n    " + yaml.dump({'fallback-' + ip: access_data})
    txn = redis_shell.pipeline()
    txn.hset('server->config', name, cfg)
    txn.lpush(REGION + ":srvq", "%s|%s|%s" % (ip, name, cfg))
    txn.execute()

def register_vps(name):
    print "Registering VPS", name
    redis_shell.rpush(CM + ':vpss', name)
    redis_shell.incr(CM + ':vpss:version')


if __name__ == '__main__':
    run()
