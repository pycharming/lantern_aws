#!/usr/bin/env python

import json
import logging
from functools import wraps
import subprocess
import os.path
import re

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
    d_in = json.load(file('{{ fallback_json_file }}'))
    # we call this 'addr' and not 'v4addr' for backwards compatibility reasons.
    d_out = {'addr': '%s:%s' % (d_in['ipv4'], d_in['port']),
             'authtoken': d_in['auth_token']}

    # At least in DO, a VPS with IPv6 disabled will still get link-local
    # addresses reported in grains. These can only cause confusion to clients
    # so let's filter them out.
    ipv6 = d_in.get('ipv6')
    if ipv6 and not ipv6.startswith('fe80'):  # link-local address prefix
        v6addr = '[%s]:%s' % (d_in['ipv6'], d_in['port'])
    else:
        v6addr = ""
    d_out['v6addr'] = v6addr

    {% if obfs4_port != 0 %}
    add_obfs4_access_data(d_out)
    {% else %}
    add_http_access_data(d_out)
    {% endif %}

    json.dump(d_out, file('/home/lantern/access_data.json', 'w'), indent=4)

def add_http_access_data(d_out):
    d_out['cert'] = subprocess.check_output(["cat", "/home/lantern/cert.pem"])

def add_obfs4_access_data(d_out):
    d_out['pluggabletransport'] = 'obfs4'
    p = re.compile('Bridge obfs4.+cert=([^ ]+) iat-mode=([0-9])')
    with open('obfs4_bridgeline.txt') as f:
        for line in f:
            m = p.match(line)
            if m:
                d_out['cert'] = m.group(1)
                d_out['pluggabletransportsettings'] = {'iat-mode': m.group(2)}

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename='/home/lantern/save_access_data.log',
                        format='%(levelname)-8s %(message)s')
    save_access_data()
