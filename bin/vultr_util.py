#!/usr/bin/env python

from datetime import datetime
import os

from vultr.vultr import Vultr


api_key = os.getenv("VULTR_APIKEY")
tokyo_dcid = u'25'
planid_768mb = u'31'
planid_1gb = u'106'
ubuntu14_04_64bit = u'160'
aranhoide_ssh_key_id = u'55255a40b2742'

bootstrap_tmpl = "ssh -o StrictHostKeyChecking=no root@%s 'curl -L https://raw.githubusercontent.com/saltstack/salt-bootstrap/902da734465798edb3aa6a68445ada358a69b0ef/bootstrap-salt.sh | sh -s -- -A 128.199.93.248 -i %s git v2014.7.0'"
vltr = Vultr(api_key)

def ip_prefix(ip):
    return ip[:ip.rfind('.', 0, ip.rfind('.'))+1]

def ip_prefixes():
    return set(ip_prefix(d['main_ip'])
               for d in vltr.server_list(None).itervalues()
               if d['label'].startswith('fl-jp-'))

def minion_id(prefix, n):
    return '%s-jp-%s-%s' % (
        prefix,
        datetime.now().date().isoformat().replace('-', ''),
        str(n).zfill(3))

def create(prefix, start, number):
    for i in xrange(start, start+number):
        label = minion_id(prefix, i)
        print "Creating %s ..." % label
        print vltr.server_create(tokyo_dcid,
                                 planid_1gb,
                                 ubuntu14_04_64bit,
                                 label=label,
                                 enable_private_network="yes",
                                 sshkeyid=aranhoide_ssh_key_id)

def install_salt(prefix, start, number):
    server_ips = {d['label']: d['main_ip']
                  for d in vltr.server_list(None).itervalues()}
    for i in xrange(start, start+number):
        label = minion_id(prefix, i)
        if label not in server_ips:
            print "No server with label %r" % label
        elif not server_ips[label]:
            print "No ip for server %s" % label
        else:
            ip = server_ips[label]
            print "Installing salt in %s (%s) ..." % (label, ip)
            os.system(bootstrap_tmpl % (ip, label))

