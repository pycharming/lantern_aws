#!/usr/bin/env python


import os
import time

from redis_util import redis_shell
import redisq
import vps_util


TIMEOUT = 5 * 60


def run():
    cm = vps_util.my_cm()
    print "Cloudmaster ID", cm
    qname = cm + ":retireq"
    destroy_qname = cm + ":destroyq"
    q = redisq.Queue(qname, redis_shell, TIMEOUT)
    while True:
        task, remover = q.next_job()
        if task:
            name, ip = task.split('|')
            print "Retiring", name, ip
            vps_util.retire_lcs(name, ip)
            txn = redis_shell.pipeline()
            remover(txn)
            # Introduce the job with the timestamp already filled in, so it will
            # only be pulled when it 'expires'. This effectively adds a delay to
            # give clients some time to move over to their new server before we
            # actually destroy the old one.
            txn.lpush(destroy_qname, "%s*%s" % (name, int(time.time())))
            txn.execute()
        else:
            time.sleep(10)


if __name__ == '__main__':
    run()
