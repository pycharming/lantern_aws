import os.path
import sys

import here

# Values for production deployment.
aws_region = 'ap-southeast-1'
default_profile = 'do'
salt_version = 'v2014.7.0'
do_region = 'Singapore 1'
# Set this to False unless you know that the datacenter supports it.
private_networking = True
controller = production_controller = 'lanternctrl1-2'
cloudmaster_name = 'production-cloudmaster'
free_for_all_sg_name = 'free-for-all'

# To override values locally, put them in config_overrides.py (not version controlled)
#controller = 'fakectrl'
#cloudmaster_name = 'fakecloudmaster'

#controller = 'lantern-controller-afisk'
#cloudmaster_name = 'fisk-cloudmaster'

#controller = 'lanternctrltest'
#cloudmaster_name = 'aranhoide-cloudmaster'

#controller = 'oxlanternctrl'
#cloudmaster_name = 'oxcloudmaster'

#installer_bucket = 'lantern-installers'
#installer_filename = 'lantern-fallback.deb'

try:
    # Import local config overrides if available
    from config_overrides import *
except ImportError:
    pass

# Derived, but may still want to override?
key_path = os.path.join(here.secrets_path,
                        'lantern_aws',
                        'cloudmaster.id_rsa')

print >> sys.stderr, "Using controller: %s" % controller
print >> sys.stderr, "Using cloudmaster: %s" % cloudmaster_name
