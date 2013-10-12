#!/usr/bin/env python

# Script to retrofit pillars to existing instances.  In this case we are feeding the
# instance_id pillar.
#
# Run as root in the cloudmaster.

import os

import yaml


PILLAR_DIR = '/srv/pillar'


for filename in os.listdir(PILLAR_DIR):
    if filename.startswith('fp-') and filename.endswith('.sls'):
        path = os.path.join(PILLAR_DIR, filename)
        instance_id = filename[:-4]
        print "processing", instance_id
        d = yaml.load(file(path))
        d['instance_id'] = instance_id
        yaml.dump(d, file(path, 'w'))
os.system("salt 'fp-*' saltutil.refresh_pillar")
