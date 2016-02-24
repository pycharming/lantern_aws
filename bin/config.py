import os
import os.path
import sys

import here

# Values for production deployment.
salt_version = 'v2015.5.5'
production_cloudmasters = ['cm-doams3', 'cm-dosgp1', 'cm-vltok1']
datacenter = os.getenv("DC", 'doams3')
cloudmaster_name = 'cm-' + datacenter
cloudmaster_address = {'doams3':  '188.166.35.238',
                       'dosgp1': '128.199.84.79',
                       'vltok1': '45.32.47.4',
                       'vlfra1': '45.63.116.130'}[datacenter]

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
