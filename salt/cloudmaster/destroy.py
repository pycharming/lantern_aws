#!/usr/bin/env python


import os
import time

from redis_util import redis_shell
import redisq
import vps_util


TIMEOUT = 4 * 60 * 60


def run():
    qname = vps_util.my_cm() + ":destroyq"
    region = vps_util.my_region()
    q = redisq.Queue(qname, redis_shell, TIMEOUT)
    print "Starting retire server in cloudmaster %s, region %s." % (vps_util.my_cm(), region)
    while True:
        name, remover = q.next_job()
        if name:
            if redis_shell.sismember(region + ":bakedin-names", name):
                print "Not retiring baked-in server", name
            else:
                print "Destroying", name
                vps_util.destroy_vps(name)
            remover()
        else:
            time.sleep(10)


if __name__ == '__main__':
    run()
