import os
import os.path
import sys

import here

# Values for production deployment.
salt_version = 'v2015.8.8.2'
production_cloudmasters = ['cm-doams3', 'cm-dosgp1', 'cm-dosfo1', 'cm-donyc3', 'cm-vltok1']
datacenter = os.getenv("DC", 'doams3')
cloudmaster_name = 'cm-' + datacenter
cloudmaster_address = {'doams3':  '188.166.35.238',
                       'dosgp1': '128.199.84.79',
                       'dosfo1': '45.55.14.51',
                       'donyc3': '159.203.73.43',
                       'vltok1': '45.32.47.4',
                       'lisgp1': '139.162.60.251',
                       'litok1': '106.185.34.20'}[datacenter]

# To override values locally, put them in config_overrides.py (not version controlled)
try:
    # Import local config overrides if available
    from config_overrides import *
except ImportError:
    pass


# Derived, but may still want to override?
key_path = os.path.join(here.secrets_path,
                        'lantern_aws',
                        'cloudmaster.id_rsa')

print >> sys.stderr, "Using cloudmaster: %s(%s)" % (cloudmaster_name, cloudmaster_address)
