import here
import os.path

# Values for production deployment.
aws_region = 'ap-southeast-1'
aws_credential_path = os.path.join(here.secrets_path,
                                   'lantern_aws',
                                   'aws_credential')
salt_version = '0.17.4'
do_region = 'New York 2'
controller = 'lanternctrl'
cloudmaster_name = 'cloudmaster'
free_for_all_sg_name = 'free-for-all'
installer_bucket = 'lantern'
installer_filename = 'latest-64.deb'

# To override values locally, put them in config_overrides.py (not version controlled)
#config.controller = 'fakectrl'
#config.cloudmaster_name = 'fakecloudmaster'

#config.controller = 'lantern-controller-afisk'
#config.cloudmaster_name = 'cloudmaster-afisk'

#config.controller = 'lanternctrltest'
#config.cloudmaster_name = 'aranhoide-cloudmaster'

#config.controller = 'oxlanternctrl'
#config.cloudmaster_name = 'oxcloudmaster'

#config.controller = 'pantscontroller'
#config.cloudmaster_name = '_pantscloudmaster'

#config.installer_bucket = 'lantern-installers'
#config.installer_filename = 'lantern-fallback.deb'

try:
    # Import local config overrides if available
    import config_overrides
except:
    pass

# Derived, but may still want to override?
key_path = os.path.join(here.secrets_path,
                        'lantern_aws',
                        aws_region + ".pem")

print "Using controller: %s" % controller
print "Using cloudmaster: %s" % cloudmaster_name