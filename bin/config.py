import here
import os.path

# Values for production deployment.
aws_region = 'ap-southeast-1'
aws_credential_path = os.path.join(here.secrets_path,
                                   'lantern_aws',
                                   'aws_credential')
salt_version = '0.16.0'
do_region = 'Amsterdam 1'
controller = 'lanternctrl'
cloudmaster_name = 'cloudmaster'
free_for_all_sg_name = 'free-for-all'

# Override with values for testing.
#controller = 'fakectrl'
#cloudmaster_name = 'fakecloudmaster'
#aws_region = 'us-east-1'
controller = 'lanternctrltest'
cloudmaster_name = 'aranhoide-cloudmaster'

# Derived, but may still want to override?
key_path = os.path.join(here.secrets_path,
                        'lantern_aws',
                        aws_region + ".pem")
