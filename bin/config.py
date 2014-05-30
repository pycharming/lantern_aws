import here
import os.path

# Values for production deployment.
aws_region = 'ap-southeast-1'
aws_credential_path = os.path.join(here.secrets_path,
                                   'lantern_aws',
                                   'aws_credential')
salt_version = '2014.1.3'
do_region = 'New York 2'
controller = 'lanternctrl1-2'
cloudmaster_name = 'cloudmaster1-2'
free_for_all_sg_name = 'free-for-all'
installer_bucket = 'lantern'
installer_filename = 'latest-64.deb'

# To override values locally, put them in config_overrides.py (not version controlled)
#controller = 'fakectrl'
#cloudmaster_name = 'fakecloudmaster'

#controller = 'lantern-controller-afisk'
#cloudmaster_name = 'cloudmaster-afisk'

#controller = 'lanternctrltest'
#cloudmaster_name = 'aranhoide-cloudmaster'

#controller = 'oxlanternctrl'
#cloudmaster_name = 'oxcloudmaster'

#controller = 'pantscontroller'
#cloudmaster_name = '_pantscloudmaster'

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

print "Using controller: %s" % controller
print "Using cloudmaster: %s" % cloudmaster_name
