from datetime import datetime
import os
import socket
import sys
import tempfile
import time
import traceback

from vultr.vultr import Vultr, VultrError

import vps_util
from vps_util import trycmd


api_key = os.getenv("VULTR_APIKEY")
tokyo_dcid = u'25'
planid_768mb = u'31'
planid_1gb = u'106'
ubuntu14_04_64bit = u'160'

# XXX: feed cloudmaster's internal IP when we launch one in Tokyo.
def ssh_tmpl(ssh_cmd):
    return "sshpass -p %s ssh -o StrictHostKeyChecking=no root@%s " + ("'%s'" % ssh_cmd)

#bootstrap_tmpl = ssh_tmpl("curl -L https://raw.githubusercontent.com/saltstack/salt-bootstrap/902da734465798edb3aa6a68445ada358a69b0ef/bootstrap-salt.sh | sh -s -- -X -A 128.199.93.248 -i %s git v2014.7.0")
bootstrap_tmpl = ssh_tmpl("curl -L https://raw.githubusercontent.com/saltstack/salt-bootstrap/902da734465798edb3aa6a68445ada358a69b0ef/bootstrap-salt.sh | sh -s -- -X -A 188.166.52.119 -i %s git v2014.7.0")

scpkeys_tmpl = "sshpass -p %s scp -p -C -o StrictHostKeyChecking=no minion.pem minion.pub root@%s:/etc/salt/pki/minion/"

fetchaccessdata_tmpl = "sshpass -p %s scp -o StrictHostKeyChecking=no root@%s:/home/lantern/access_data.json ."

start_tmpl = ssh_tmpl("service salt-minion restart")

reboot_tmpl = ssh_tmpl("reboot")

vultr = Vultr(api_key)


def ip_prefix(ip):
    return ip[:ip.rfind('.', 0, ip.rfind('.'))+1]

def ip_prefixes():
    return set(ip_prefix(d['main_ip'])
               for d in vultr.server_list(None).itervalues()
               if d['label'].startswith('fl-jp-'))

def minion_id(prefix, n):
    return '%s-jp-%s-%s' % (
        prefix,
        datetime.now().date().isoformat().replace('-', ''),
        str(n).zfill(3))

def create_vps(label):
    return vultr.server_create(tokyo_dcid,
                               planid_1gb,
                               ubuntu14_04_64bit,
                               label=label,
                               enable_private_network="yes")['SUBID']

def wait_for_status_ok(subid):
    while True:
        try:
            d = vultr.server_list(subid)
            if (d['status'] == 'active'
                and d['power_status'] == 'running'
                and d['server_state'] == 'ok'):
                return d
        except VultrError:
            traceback.print_exc()
        print "Server not started up; waiting..."
        time.sleep(10)

def init_vps(subid):
    # VPSs often (always?) report themselves as OK before stopping and
    # completing setup. Trying to initialize them at this early stage seems to
    # cause trouble.
    wait_for_status_ok(subid)
    print "Status OK for the first time.  I don't buy it.  Lemme wait again..."
    time.sleep(10)
    while True:
        d = wait_for_status_ok(subid)
        print "Status OK again; bootstrapping..."
        ip = d['main_ip']
        name = d['label']
        passw = d['default_password']
        if os.system(bootstrap_tmpl % (passw, ip, name)):
            print "Error trying to bootstrap; retrying..."
        else:
            break
        time.sleep(5)
    print "Generating and copying keys..."
    with vps_util.tempdir(subid):
        trycmd('salt-key --gen-keys=%s' % name)
        for suffix in ['.pem', '.pub']:
            os.rename(name + suffix, 'minion' + suffix)
        trycmd(scpkeys_tmpl % (passw, ip))
        os.rename('minion.pub', os.path.join('/etc/salt/pki/master/minions', name))
        print "Starting salt-minion..."
        trycmd(start_tmpl % (passw, ip))
        vps_util.save_pillar(name)
        print "Calling highstate..."
        time.sleep(10)
        trycmd("salt -t 1800 %s state.highstate" % name)
        return vps_util.hammer_the_damn_thing_until_it_proxies(
            name,
            reboot_tmpl % (passw, ip),
            fetchaccessdata_tmpl % (passw, ip))

def create_bunch(prefix, start, number):
    for i in xrange(start, start+number):
        label = minion_id(prefix, i)
        print "Creating %s ..." % label
        print create_vps(label)

def install_salt(prefix, start, number):
    server_ips = {d['label']: d['main_ip']
                  for d in vultr.server_list(None).itervalues()}
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

