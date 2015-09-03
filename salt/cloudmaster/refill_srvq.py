#!/usr/bin/env python


from datetime import datetime
import multiprocessing
from Queue import Empty
from redis_util import redis_shell
import os
import time
import traceback

import yaml

import redisq


MAXPROCS = int(os.getenv('MAXPROCS'))
LAUNCH_TIMEOUT = 60 * 60


def run():
    dc = os.getenv("DC")
    print "Using datacenter", dc, ", MAXPROCS", repr(MAXPROCS)
    qname = dc + ":srvreqq"
    reqq = redisq.Queue(qname, redis_shell, LAUNCH_TIMEOUT)
    procq = multiprocessing.Queue()
    pending = {}
    def kill_task(reqid):
        print "Killing timed out process and vps..."
        task = pending.pop(reqid)
        task['proc'].terminate()
        proc = multiprocessing.Process(target=vps_shell(dc).destroy_vps,
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
                    upload_cfg(redis_shell, dc, result['access_data'])
                    register_vps(redis_shell, dc, task['name'])
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
                name = get_lcs_name(dc, redis_shell)
                proc = multiprocessing.Process(target=launch_one_server,
                                               args=(procq,
                                                     reqid,
                                                     dc,
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

def vps_shell(dc):
    if dc.startswith('vl'):
        import vultr_util
        return vultr_util
    elif dc.startswith('do'):
        import do_util
        return do_util

def get_lcs_name(dc, redis_shell):

    if dc.startswith('vltok'):
        country = 'jp'
    elif dc.startswith('doams'):
        country = 'nl'
    else:
        assert False

    now = datetime.utcnow()
    date = "%d%02d%02d" % (now.year, now.month, now.day)

    if redis_shell.get(dc + ':lcsserial:date') == date:
        serial = redis_shell.incr(dc + ':lcsserial')
    else:
        pipe = redis_shell.pipeline()
        pipe.set(dc + ':lcsserial:date', date)
        pipe.set(dc + ':lcsserial', 1)
        pipe.execute()
        serial = 1

    return 'fp-%s-%s-%03d' % (country, date, serial)

def launch_one_server(q, reqid, dc, name):
    vs = vps_shell(dc)
    q.put({'reqid': reqid,
           'name': name,
           'access_data': vs.init_vps(vs.create_vps(name))})

def upload_cfg(redis_shell, dc, access_data):
    ip = access_data['addr'].split(':')[0]
    # DRY: flashlight/genconfig/cloud.yaml.tmpl
    access_data.update(pipeline=True,
                       trusted=True,
                       qos=10,
                       weight=1000000)
    redis_shell.rpush(dc + ":srvq",
                      "%s|\n    %s" % (ip, yaml.dump({'fallback-' + ip: access_data})))

def register_vps(redis_shell, dc, name):
    print "Registering VPS", name
    redis_shell.rpush(dc + ':vpss', name)
    redis_shell.incr(dc + ':vpss:version')


if __name__ == '__main__':
    run()