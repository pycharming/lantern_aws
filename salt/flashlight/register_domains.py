#!/usr/bin/env python

import logging
import os
import sys

import pyflare
import yaml


CF_ID = "{{ pillar['cf_id'] }}"
CF_KEY = "{{ pillar['cf_key'] }}"
INSTANCE_ID = "{{ grains['id'] }}"
IP = '{{ grains["ipv4"][0] if grains["ipv4"][0] != "127.0.0.1" else grains["ipv4"][1] }}'
DOMAIN = 'getiantem.org'
RECORDS_FILE = '{{ domain_records_file }}'


def register():
    cf = pyflare.Pyflare(CF_ID, CF_KEY)
    record_ids = []
    for subdomain in ["roundrobin", INSTANCE_ID]:
        response = cf.rec_new(DOMAIN, 'A', subdomain, IP)
        check_response(response, record_ids)
        record_id = response['response']['rec']['obj']['rec_id']
        record_ids.append(record_id)
        # Set service_mode to "orange cloud".  For some reason we can't do this
        # on rec_new.
        response = cf.rec_edit(DOMAIN, 'A', record_id, subdomain, IP, service_mode=1)
        check_response(response, record_ids)
        yaml.dump(record_ids, file(RECORDS_FILE, 'w'))

def check_response(response, record_ids):
    if response['result'] != 'success':
        logging.error("Bad result: %s" % response['result'])
        for record_id in record_ids:
            cf.rec_delete(DOMAIN, record_id)
        sys.exit(1)

def unregister():
    cf = pyflare.Pyflare(CF_ID, CF_KEY)
    record_ids = yaml.load(file(RECORDS_FILE))
    assert isinstance(record_ids, list) and len(record_ids) == 2
    all_ok = True
    for record_id in record_ids:
        response = cf.rec_delete(DOMAIN, record_id)
        if response['result'] == 'success':
            logging.info("Deleted record %s" % record_id)
        else:
            all_ok = False
            logging.warn("Couldn't delete record %s: %s"
                         % (record_id, response['result']))
    if all_ok:
        os.remove(RECORDS_FILE)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename="register_domains.log",
                        format='%(asctime)s %(levelname)-8s %(message)s')
    try:
        if (len(sys.argv) == 1
            or (len(sys.argv) == 2
                and sys.argv[1] == 'register')):
            register()
        elif (len(sys.argv) == 2
              and sys.argv[1] == 'unregister'):
            unregister()
        else:
            print "Usage: %s [register(default)|unregister]" % sys.argv[0]
    except:
        logging.exception("uncaught top-level exception")
        sys.exit(1)




