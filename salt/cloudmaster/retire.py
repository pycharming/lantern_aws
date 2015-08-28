#!/usr/bin/env python


import os
import time

from redis_util import redis_shell
import redisq
import vps_util


TIMEOUT = 5 * 60


def run():
    dc = os.getenv("DC")
    print "Using datacenter", dc
    qname = dc + ":retireq"
    destroy_qname = dc + ":destroyq"
    q = redisq.Queue(qname, redis_shell, TIMEOUT)
    while True:
        task, remover = q.next_job()
        if task:
            name, ip = task.split('|')
            print "Retiring", name, ip
            vps_util.retire_lcs(name, ip)
            txn = redis_shell.pipeline()
            remover(txn)
            txn.lpush(destroy_qname, "%s*%s" % (name, int(time.time())))
            txn.execute()
        time.sleep(10)


if __name__ == '__main__':
    run()
