#!/usr/bin/env python


import multiprocessing
from Queue import Empty
import os
import time
import traceback
import random

import yaml
import json

from alert import send_to_slack
from redis_util import redis_shell
import redisq
import vps_util


CM = vps_util.my_cm()
REGION = vps_util.my_region()
scope = os.environ['QSCOPE']
if scope == 'REGION':
    QPREFIX = REGION
elif scope == 'CM':
    QPREFIX = CM
else:
    assert False
MAXPROCS = int(os.getenv('MAXPROCS'))
LAUNCH_TIMEOUT = 30 * 60

vps_shell = vps_util.vps_shell(CM)


def run():
    qname = QPREFIX + ":srvreqq"
    print "Serving queue", qname, ", MAXPROCS:", repr(MAXPROCS)
    quarantine = CM + ":quarantined_vpss"
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
        # If the request queue is totally empty (no tasks enqueued or even in
        # progress), flush the quarantine queue into the destroy queue.
        if redis_shell.llen(qname) == 1:  # 1 for the redisq sentinel entry
            names = redis_shell.smembers(quarantine)
            if names:
                print "Flushing %s VPSs from quarantine." % len(names)
                p = redis_shell.pipeline()
                p.srem(quarantine, *names)
                p.lpush(CM + ":destroyq", *names)
                p.execute()
        while not procq.empty():
            try:
                result = procq.get(False)
                print "Got result:", result
                task = pending.get(result['reqid'])
                if task and task['name'] == result['name']:
                    p = redis_shell.pipeline()
                    if result['blocked']:
                        print "Quarantining %(name)s (%(ip)s)." % result
                        p.sadd(quarantine, result['name'])
                        p.incr(CM + ":blocked_vps_count")  # stats
                        # We'll remove the original request anyway because we
                        # don't want it to stay around until timeout. Insert a
                        # new one to replace it instead.
                        reqid = redis_shell.incr('srvcount')
                        p.lpush(qname, reqid)
                    else:
                        p.incr(CM + ":unblocked_vps_count")  # stats
                        del pending[result['reqid']]
                        vps_util.enqueue_cfg(result['name'], result['access_data'], result['srvq'])
                        register_vps(task['name'])
                    task['remove_req'](p)
                    p.execute()
            except Empty:
                print "Wat?"
                break
        if len(pending) < MAXPROCS:
            req_string, remover = reqq.next_job()
            if req_string:
                print "Got request", req_string
                req = json.loads(req_string)
                if isinstance(req, int):
                    # Transition: support the old format while we are updating
                    # the config server etc.
                    # We also randomize whether it's obfs4 or not, and which
                    # port to use.
                    proxy_port = 443
                    obfs4_port = 0
                    if random.random() > 0.5:
                        # Pick a random high port higher than salt port 4506
                        proxy_port = random.randint(5000, 60000)
                    if random.random() > 0.5:
                        # Make this an obfs4 proxy
                        obfs4_port = proxy_port
                    req = { 'id': req,
                            'srvq': QPREFIX + ':srvq',
                            'proxy_port': proxy_port,
                            'obfs4_port': obfs4_port }
                    req_string = json.dumps(req)
                reqid = req['id']
                if reqid in pending:
                    print "Killing task %s because of queue timeout" % reqid
                    kill_task(reqid)
                name = new_proxy_name(req)
                proc = multiprocessing.Process(target=launch_one_server,
                                               args=(procq,
                                                     reqid,
                                                     name,
                                                     req_string))
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

def new_proxy_name(req):
    type_str = 'obfs4' if req.get('obfs4_port', 0) > 0 else 'https'
    return vps_util.new_vps_name('fp-' + type_str)

def launch_one_server(q, reqid, name, req_string):
    req = json.loads(req_string)
    d = vps_shell.create_vps(name, req)
    ip = d['ip']
    msg = {'reqid': reqid,
           'name': name,
           'ip': ip,
           'srvq': req['srvq'],
           'access_data': None}
    if redis_shell.sismember(REGION + ':blocked_ips', ip):
        msg['blocked'] = True
    else:
        access_data = vps_shell.init_vps(d)
        #XXX: DRY
        adip = access_data['addr'].split(':')[0]
        if adip != ip:
            print "IP mismatch! %s != %s" % (adip, ip)
            send_to_slack("IP mismatch",
                          "Proxy which reported IP %s on creation has IP %s in access_data" % (ip, adip),
                          color="#ff00ff")
            msg['ip'] = adip
        if redis_shell.sismember(REGION + ":blocked_ips", adip):
            print "Blocked IP %s sneaked in!" % adip
            send_to_slack("Blocked IP sneaked in",
                          "Blocked IP %s was sneaking into %s's cloudmaster" % (adip, CM),
                          color="danger")
            msg['blocked'] = True
        else:
            msg['blocked'] = False
            msg['access_data'] = access_data
    q.put(msg)


def register_vps(name):
    print "Registering VPS", name
    redis_shell.rpush(CM + ':vpss', name)
    redis_shell.incr(CM + ':vpss:version')


if __name__ == '__main__':
    run()
