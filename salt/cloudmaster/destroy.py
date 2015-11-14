#!/usr/bin/env python


import os
import time

from redis_util import redis_shell
import redisq
import vps_util


TIMEOUT = 4 * 60 * 60


def run():
    dc = os.getenv("DC")
    print "Using datacenter", dc
    qname = dc + ":destroyq"
    q = redisq.Queue(qname, redis_shell, TIMEOUT)
    while True:
        name, remover = q.next_job()
        if name:
            print "Destroying", name
            vps_util.destroy_vps(name)
            remover()
        else:
            time.sleep(10)


if __name__ == '__main__':
    run()
