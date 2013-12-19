import here
import os.path

# Values for production deployment.
aws_region = 'ap-southeast-1'
aws_credential_path = os.path.join(here.secrets_path,
                                   'lantern_aws',
                                   'aws_credential')
salt_version = '0.16.0'
do_region = 'New York 2'
controller = 'lanternctrl'
cloudmaster_name = 'cloudmaster'
free_for_all_sg_name = 'free-for-all'
installer_bucket = 'lantern'
installer_filename = 'latest-64.deb'

# Override with values for testing.
#controller = 'fakectrl'
#cloudmaster_name = 'fakecloudmaster'

#controller = 'lantern-controller-afisk'
#cloudmaster_name = 'cloudmaster-afisk'

#controller = 'lanternctrltest'
#cloudmaster_name = 'aranhoide-cloudmaster'

controller = 'oxlanternctrl'
cloudmaster_name = 'oxcloudmaster'

#controller = 'pantscontroller'
#cloudmaster_name = '_pantscloudmaster'

#installer_bucket = 'lantern-installers'
#installer_filename = 'lantern-fallback.deb'

# Derived, but may still want to override?
key_path = os.path.join(here.secrets_path,
                        'lantern_aws',
                        aws_region + ".pem")
