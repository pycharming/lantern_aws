import os

here = os.path.dirname(__file__)
salt_states_path = os.path.join(here, '..', 'salt')
bootstrap_path = os.path.join(here, '..', 'etc', 'bootstrap.bash')
secrets_path = os.path.join(here, '..', 'secret', 'build-installers')
