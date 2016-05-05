#!/usr/bin/env python


import json
import os
import time

from redis_util import redis_shell
import redisq
import vps_util


TIMEOUT = 5 * 60


def run():
    region = vps_util.my_region()
    print "Starting offload server for region %s." % region
    qname = region + ":offloadq"
    q = redisq.Queue(qname, redis_shell, TIMEOUT)
    while True:
        task, remover = q.next_job()
        if task:
            try:
                task = json.loads(task)
            except ValueError:
                # transition
                name, ip = task.split('|')
                task = {'name': name, 'ip': ip, 'proportion': 1.0, 'replace': True}
            print "Offloading users from %s (%s)" % (name, ip)
            txn = redis_shell.pipeline()
            vps_util.actually_offload_proxy(proportion=task['proportion'],
                                            replace=task['replace'],
                                            name=task['name'],
                                            ip=task['ip'],
                                            pipeline=txn)
            remover(txn)
            cm = vps_util.cm_by_name(name)
            txn.lpush(cm + ':retireq', '%s|%s' % (task['name'], task['ip']))
            txn.execute()
        else:
            time.sleep(10)


if __name__ == '__main__':
    run()
