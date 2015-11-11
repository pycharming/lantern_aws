{% set fallback_json_file='/home/lantern/fallback.json' %}
{% set proxy_protocol=pillar.get('proxy_protocol', 'tcp') %}
{% set auth_token=pillar.get('auth_token') %}
{% set proxy_port=grains.get('proxy_port', 62443) %}
{% set traffic_check_period_minutes=60 %}
{% from 'ip.sls' import external_ip %}

fp-dirs:
  file.directory:
    - names:
        - /var/log/http-proxy
    - user: lantern
    - group: lantern
    - mode: 755
    - makedirs: yes
    - recurse:
        - user
        - group
        - mode

# To filter through jinja.
{% set template_files=[
    ('/etc/init/', 'http-proxy.conf', 'http-proxy.conf', 'root', 644),
    ('/home/lantern/', 'util.py', 'util.py', 'lantern', 400),
    ('/home/lantern/', 'check_load.py', 'check_load.py', 'lantern', 700),
    ('/home/lantern/', 'check_traffic.py', 'check_traffic.py', 'lantern', 700),
    ('/home/lantern/', 'auth_token.txt', 'auth_token.txt', 'lantern', 400),
    ('/home/lantern/', 'fallback.json', 'fallback.json', 'lantern', 400)] %}

# To copy verbatim.
{% set nontemplate_files=[
    ('/usr/local/bin/', 'badvpn-udpgw', 'badvpn-udpgw', 'root', 755),
    ('/etc/init.d/', 'badvpn-udpgw', 'udpgw-init', 'root', 755)] %}

include:
    - proxy_ufw_rules
    - redis

{% for dir,dst_filename,src_filename,user,mode in template_files %}
{{ dir+dst_filename }}:
    file.managed:
        - source: salt://fallback_proxy/{{ src_filename }}
        - template: jinja
        - context:
            auth_token: {{ auth_token }}
            external_ip: {{ external_ip(grains) }}
            traffic_check_period_minutes: {{ traffic_check_period_minutes }}
        - user: {{ user }}
        - group: {{ user }}
        - mode: {{ mode }}
        - require:
            - file: fp-dirs
{% endfor %}

{% for dir,dst_filename,src_filename,user,mode in nontemplate_files %}
{{ dir+dst_filename }}:
    file.managed:
        - source: salt://fallback_proxy/{{ src_filename }}
        - user: {{ user }}
        - group: {{ user }}
        - mode: {{ mode }}
        - require:
            - file: fp-dirs
{% endfor %}


fallback-proxy-dirs-and-files:
    cmd.run:
        - name: ":"
        - require:
            {% for dir,dst_filename,src_filename,user,mode in template_files %}
            - file: {{ dir+dst_filename }}
            {% endfor %}
            {% for dir,dst_filename,src_filename,user,mode in nontemplate_files %}
            - file: {{ dir+dst_filename }}
            {% endfor %}

save-access-data:
    cmd.script:
        - source: salt://fallback_proxy/save_access_data.py
        - template: jinja
        - context:
            fallback_json_file: {{ fallback_json_file }}
        - user: lantern
        - group: lantern
        - cwd: /home/lantern
        - require:
            - file: {{ fallback_json_file }}
            - cmd: convert-cert

zip:
    pkg.installed

requests:
  pip.installed

/home/lantern/report_stats.py:
    cron.absent:
        - user: lantern


{% if pillar['in_production'] %}

"/home/lantern/check_load.py 2>&1 | logger -t check_load":
  cron.present:
    - minute: "*/7"
    - user: lantern
    - require:
        - file: /home/lantern/check_load.py
        - pip: requests
        - cron: REDIS_URL
        - pkg: python-redis

"/home/lantern/check_traffic.py 2>&1 | logger -t check_traffic":
  cron.absent:
    - user: lantern
#  cron.present:
#    - minute: "*/{{ traffic_check_period_minutes }}"
#    - user: lantern
#    - require:
#        - file: /home/lantern/check_traffic.py
#        - pip: psutil

{% if grains['id'].startswith('fp-jp-') %}

vultr:
  pip.installed:
    - name: vultr==0.1.2

/home/lantern/check_vultr_transfer.py:
    file.managed:
        - source: salt://fallback_proxy/check_vultr_transfer.py
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: 700

"/home/lantern/check_vultr_transfer.py 2>&1 | logger -t check_vultr_transfer":
  cron.present:
    - identifier: check_vultr_transfer
    - minute: random
    - user: lantern
    - require:
        - file: /home/lantern/check_vultr_transfer.py
        - pip: vultr
        - cron: REDIS_URL
        - pkg: python-redis

{% endif %}

{% endif %}

REDIS_URL:
  cron.env_present:
    - user: lantern
    - value: {{ pillar['cfgsrv_redis_url'] }}

# Dictionary of American English words for the dname generator in
# generate-cert.
wamerican:
    pkg.installed

tcl:
    pkg.installed

generate-cert:
    cmd.script:
        - source: salt://fallback_proxy/gencert.py
        - template: jinja
        # Don't clobber the keystore of old fallbacks.
        - creates: /home/lantern/littleproxy_keystore.jks
        - require:
            - pkg: wamerican

install-http-proxy:
    cmd.script:
        - source: salt://fallback_proxy/install_http_proxy.sh
        - user: lantern
        - group: lantern

convert-cert:
    cmd.script:
        - source: salt://fallback_proxy/convcert.sh
        - creates: /home/lantern/key.pem
        - user: lantern
        - group: lantern
        - mode: 400
        - require:
            - cmd: generate-cert

proxy-service:
    service.running:
        - name: http-proxy
        - enable: yes
        - watch:
            - cmd: fallback-proxy-dirs-and-files
            - cmd: convert-cert
        - require:
            - pkg: tcl
            - cmd: ufw-rules-ready
            - cmd: install-http-proxy
            - service: ats-disabled
            - service: lantern-disabled
            - service: badvpn-udpgw
        - watch:
            - file: /etc/init.d/http-proxy

badvpn-udpgw:
  service.running:
    - enable: yes
    - watch:
        - cmd: fallback-proxy-dirs-and-files

# Remove cron job that tries to make sure lantern-java is working, in old
# servers.
/home/lantern/check_lantern.py:
    cron.absent:
        - user: root

ats-disabled:
    service.dead:
        - name: trafficserver
        - enable: no

# Disable Lantern-java in old servers.
lantern-disabled:
    service.dead:
        - name: lantern
        - enable: no
        - require:
            - cron: /home/lantern/check_lantern.py


# Not strictly necessary perhaps, but make sure, for good measure, that old
# lantern init scripts are not around.

/etc/init.d/lantern:
    file.absent:
        - require:
            - service: lantern-disabled

/etc/init.d/http-proxy:
    file.absent:
        - require:
            - file: /etc/init/http-proxy.conf

/etc/init.d/trafficserver:
    file.absent:
        - require:
            - service: ats-disabled