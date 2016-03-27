#!/usr/bin/env python

from alert import alert
from redis_util import redis_shell
import vps_util


def vpss_from_cm(cm):
    try:
        local_version = file(cm + '_vpss_version').read()
    except IOError:
        local_version = None
    remote_version = redis_shell.get(cm + ':vpss:version')
    if local_version == remote_version:
        return set(map(str.strip, file(cm + '_vpss')))
    else:
        ret = redis_shell.lrange(cm + ':vpss', 0, -1)
        file(cm + '_vpss', 'w').write('\n'.join(ret))
        file(cm + '_vpss_version', 'w').write(remote_version)
        return set(ret)

expected_do = vpss_from_cm('doams3') | vpss_from_cm('dosgp1') | vpss_from_cm('donyc3') | vpss_from_cm('dosfo1')
expected_vultr = vpss_from_cm('vltok1') | vpss_from_cm('vlfra1') | vpss_from_cm('vlpar1')

actual_do = set(v.name for v in vps_util.vps_shell('do').all_vpss()
                if not v.name.startswith('fp-')
                or vps_util.is_production_proxy(v.name))
actual_vultr = set(v.name for v in vps_util.vps_shell('vl').all_vpss())

errors = []
for caption, vpss in [("Missing DO droplets", expected_do - actual_do),
                      ("Unexpected DO droplets", actual_do - expected_do),
                      ("Missing Vultr VPSs", expected_vultr - actual_vultr),
                      ("Unexpected Vultr VPSs", actual_vultr - expected_vultr)]:
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
