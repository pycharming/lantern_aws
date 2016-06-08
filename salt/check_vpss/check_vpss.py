#!/usr/bin/env python

from alert import alert
from redis_util import redis_shell
import vps_util


def vpss_from_cm(cm):
    return (set(redis_shell.lrange(cm + ':vpss', 0, -1))
            | set([entry.split('*')[0]
                   for entry in redis_shell.lrange(cm + ':destroyq', 0, -1)
                   if not entry.startswith('-1')]))

dcs = {'do': ['doams3', 'dosgp1', 'donyc3', 'dosfo1'],
       'li': ['lisgp1', 'litok1']}

expected = {provider: set.union(*map(vpss_from_cm, provider_dcs))
            for provider, provider_dcs in dcs.iteritems()}

actual = {provider: set(v.name
                        for v in vps_util.vps_shell(provider).all_vpss()
                        if not v.name.startswith('fp-')
                        or vps_util.is_production_proxy(v.name))
          for provider in dcs}

errors = []
for provider in dcs:
    for caption, vpss in [(("Missing %s droplets" % provider.upper()),
                           expected[provider] - actual[provider]),
                          (("Unexpected %s droplets" % provider.upper()),
                           actual[provider] - expected[provider])]:
        if vpss:
            errors.append(caption + ": " + ", ".join(sorted(vpss)))

if errors:
    for error in errors:
        print "ERROR: ", error
    alert(type='vps-list-mismatch',
          details={'errors': errors},
          title='Mismatch in VPS list',
          text="".join(error + "\n" for error in errors))
else:
    print "No errors."
