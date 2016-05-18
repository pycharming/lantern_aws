# This version of paths.py is used when running scripts on developer machines
import os

here = os.path.dirname(__file__)
secrets = os.path.join(here, '..', 'secret')
