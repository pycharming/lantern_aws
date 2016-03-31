from datetime import datetime
import os
import random
import socket
import sys
import tempfile
import time
import traceback
from itertools import *

from vultr.vultr import Vultr, VultrError

import misc_util as util
import vps_util
from vps_util import trycmd


api_key = os.getenv("VULTR_APIKEY")
planid_1gb = u'111'
ubuntu14_04_64bit = u'160'
vultr_server_list_retries = 10
cloudmaster_keyid = u'56aa5453eef0b'

vultr_dcid = {'vltok1': u'25',
              'vlfra1': u'9',
              'vlpar1': u'24',
              'vllan1': u'5'}

default_plan = {'vltok1': u'31',
                'vlfra1': u'29',
                'vlpar1': u'29',
                'vllan1': u'29'}

# XXX: feed cloudmaster's internal IP when we launch one in Tokyo.
def ssh_tmpl(ssh_cmd):
    return "ssh -i /etc/salt/cloudmaster.id_rsa -o StrictHostKeyChecking=no root@%s " + ("'%s'" % ssh_cmd)

#{% from 'ip.sls' import external_ip %}
bootstrap_tmpl = ssh_tmpl("curl -L https://bootstrap.saltstack.com | sh -s -- -X -A {{ external_ip(grains) }} -i %s git {{ pillar['salt_version'] }}")

scpkeys_tmpl = "scp -p -C -i /etc/salt/cloudmaster.id_rsa -o StrictHostKeyChecking=no minion.pem minion.pub root@%s:/etc/salt/pki/minion/"

fetchaccessdata_tmpl = "scp -i /etc/salt/cloudmaster.id_rsa -o StrictHostKeyChecking=no root@%s:/home/lantern/access_data.json ."

start_tmpl = ssh_tmpl("service salt-minion restart")

vultr = Vultr(api_key)


def ip_prefix(ip):
    return ip[:ip.rfind('.', 0, ip.rfind('.'))+1]

def ip_prefixes():
    return set(ip_prefix(d['main_ip'])
               for d in retrying_server_list().values()
               if d['label'].startswith('fl-jp-'))

def minion_id(prefix, n):
    return '%s-jp-%s-%s' % (
        prefix,
        datetime.now().date().isoformat().replace('-', ''),
        str(n).zfill(3))

def create_vps(label, req):
    vps_util.save_pillar(label, req)
    dc = vps_util.dc_by_cm(vps_util.my_cm())
    subid = vultr.server_create(vultr_dcid[dc],
                                default_plan[dc],
                                ubuntu14_04_64bit,
                                label=label,
                                sshkeyid=cloudmaster_keyid,
                                enable_ipv6='yes',
                                enable_private_network="yes")['SUBID']
    for _ in xrange(30):
        time.sleep(10)
        d = try_vultr_cmd(vultr.server_list, subid)
        ip = d.get('main_ip')
        if ip and util.ipre.match(ip):
            d['ip'] = ip
            return d
    raise RuntimeError("Couldn't get the new VPS's IP")

def try_vultr_cmd(cmd, *args):
    "With exponential backoff, to work around Vultr's one-request-per-second limit."
    for tryno in count(1):
        try:
            return apply(cmd, args)
        except VultrError as e:
            traceback.print_exc()
            # Add some random factor too, to break synchronization between
            # concurrently starting jobs.
            time.sleep(1.5 ** tryno + random.random() * 10)
    raise e

def wait_for_status_ok(subid):
    backoff = 1
    while True:
        d = try_vultr_cmd(vultr.server_list, subid)
        if (d['status'] == 'active'
            and d['power_status'] == 'running'
            and d['server_state'] == 'ok'):
            return d
        print("Server not started up; waiting...")
        time.sleep(10)

def init_vps(d):
    subid = d['SUBID']
    wait_for_status_ok(subid)
    # VPSs often (always?) report themselves as OK before stopping and
    # completing setup. Trying to initialize them at this early stage seems to
    # cause trouble.  I don't know of any way to determine programatically when
    # it's OK to start pounding on these machines, but empirically some 400
    # seconds after status first reported OK should be fine most of the time.
    print("Status OK for the first time.  I don't buy it.  Lemme sleep some...")
    time.sleep(400)
    while True:
        d = wait_for_status_ok(subid)
        print("Status OK again; bootstrapping...")
        ip = d['main_ip']
        name = d['label']
        passw = d['default_password']
        if os.system(bootstrap_tmpl % (ip, name)):
            print("Error trying to bootstrap; retrying...")
        else:
            break
        time.sleep(10)
    print("Generating and copying keys...")
    with vps_util.tempdir(subid):
        trycmd('salt-key --gen-keys=%s' % name)
        for suffix in ['.pem', '.pub']:
            os.rename(name + suffix, 'minion' + suffix)
        trycmd(scpkeys_tmpl % ip)
        os.rename('minion.pub', os.path.join('/etc/salt/pki/master/minions', name))
        print("Starting salt-minion...")
        trycmd(start_tmpl % ip)
        print("Calling highstate...")
        time.sleep(10)
        trycmd("salt -t 1800 %s state.highstate" % name)
        return vps_util.hammer_the_damn_thing_until_it_proxies(
            name,
            ssh_tmpl('%%s') % ip,
            fetchaccessdata_tmpl % ip)

def destroy_vps(name,
                server_cache=util.Cache(timeout=60*60,
                                        update_fn=lambda: retrying_server_list().values())):
    for d in server_cache.get():
        if d['label'] == name:
            vultr.server_destroy(d['SUBID'])
            break
    time.sleep(10)
    os.system('salt-key -yd ' + name)

def dict2vps(d):
    ram_suffix = " MB"
    assert d['ram'].endswith(ram_suffix)
    ram = int(d['ram'][:-len(ram_suffix)])
    url = "https://my.vultr.com/subs/?SUBID=%s#subsusage" % d['SUBID']
    return vps_util.vps(d['label'], d['main_ip'], ram, 'vl', url, d)

def all_vpss():
    return map(dict2vps, retrying_server_list().itervalues())

def retrying_server_list():
    for _ in xrange(vultr_server_list_retries):
        ret = vultr.server_list(None)
        if ret:
            return ret
        print "vultr.server_list(None) returned an empty list; retrying..."
    raise RuntimeError("vultr.server_list(None) repeatedly returned []")
