#!/usr/bin/env python

import hashlib
import os
import sys

import redis
import yaml

from redis_util import redis_shell

def feed(src):
    p = redis_shell.pipeline(transaction=True)
    cfg = yaml.load(file(src))
    cfg['client']['frontedservers'] = []
    cfg['client']['chainedservers'] = "<SERVER CONFIG HERE>"
    globalcfg = yaml.dump(cfg)
    p.set("globalcfg", globalcfg)
    p.set("globalcfgsha", hashlib.sha1(globalcfg).hexdigest())
    p.execute()

def usage():
    print "%s [<opts>] src" % sys.argv[0]
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
    feed(sys.argv[1])
