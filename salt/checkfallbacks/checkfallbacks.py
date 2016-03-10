#!/usr/bin/env python

import json
import subprocess
import yaml

from alert import alert
from redis_util import redis_shell


prefix = 'fallbacks-to-check'
try:
    local_version = file(prefix + '-version').read()
except IOError:
    local_version = None
remote_version = redis_shell.get('srvcount')
if local_version != remote_version:
    suppress = redis_shell.smembers('checkfallbacks-suppress')
    json.dump([yaml.load(cfg).values()[0]
               for srv, cfg in redis_shell.hgetall('srv->cfg').iteritems()
               if srv not in suppress],
              file(prefix + '.json', 'w'))
    file(prefix + '-version', 'w').write(remote_version)

cmd = subprocess.Popen("checkfallbacks -fallbacks %s.json -connections 20 | grep '\[failed fallback check\]'" % prefix,
                       shell=True,
                       stdout=subprocess.PIPE)
errors = list(cmd.stdout)
if errors:
    for error in errors:
        print error
    alert(type='checkfallbacks-failures',
          details={'errors': errors},
          title='Proxy check failures',
          text="".join(error[len('[failed fallback check] '):] + "\n"
                       for error in errors),
          color="#dddd77")
else:
    print "No errors."
