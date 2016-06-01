#!/usr/bin/env python

from alert import alert
from redis_util import redis_shell
import vps_util


def vpss_from_cm(cm):
    try:
        local_version = file(cm + '_vpss_version').read()
    except IOError:
        local_version = None
    remote_version = redis_shell.get(cm + ':vpss:version') or '0'
    if local_version == remote_version:
        return set(map(str.strip, file(cm + '_vpss')))
    else:
        ret = redis_shell.lrange(cm + ':vpss', 0, -1)
        file(cm + '_vpss', 'w').write('\n'.join(ret))
        file(cm + '_vpss_version', 'w').write(remote_version)
        return set(ret)

dcs = {'do': ['doams3', 'dosgp1', 'donyc3', 'dosfo1'],
       'vl': ['vltok1'],
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
