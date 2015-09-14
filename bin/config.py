import os.path
import sys

import here

# Values for production deployment.
salt_version = 'v2015.5.5'
production_cloudmasters = []
cloudmaster_name = 'cm-doams3'
cloudmaster_address = "188.166.35.238"

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

print >> sys.stderr, "Using cloudmaster: %s" % cloudmaster_name
