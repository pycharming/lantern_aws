#!/usr/bin/env python

import json
import logging
from functools import wraps
import subprocess


PT_TYPE = {{ pillar.get('pt_type')|python }}


def log_exceptions(f):
    @wraps(f)
    def deco(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception, e:
            logging.exception(e)
            raise
    return deco

@log_exceptions
def save_access_data():
    d = json.load(file('{{ fallback_json_file }}'))
    d['cert'] = subprocess.check_output(
            ["keytool", "-exportcert",
             "-alias", "fallback",
             "-storepass", "Be Your Own Lantern",
             "-rfc",
             "-keystore", "/home/lantern/littleproxy_keystore.jks"])
    if PT_TYPE is not None:
        d['pt'] = {{ pillar.get('pt_props')|python }}
        d['pt']['type'] = PT_TYPE
    json.dump(d, file('/home/lantern/access_data.json', 'w'))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename='/home/lantern/save_access_data.log',
                        format='%(levelname)-8s %(message)s')
    save_access_data()
