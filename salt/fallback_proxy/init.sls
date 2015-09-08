{% set fallback_json_file='/home/lantern/fallback.json' %}
{% set proxy_protocol=pillar.get('proxy_protocol', 'tcp') %}
{% set auth_token=pillar.get('auth_token') %}
{% set proxy_port=grains.get('proxy_port', 62443) %}
{% set traffic_check_period_minutes=60 %}
{% from 'ip.sls' import external_ip %}

fp-dirs:
  file.directory:
    - names:
        - /opt/ts/libexec/trafficserver
        - /opt/ts/etc/trafficserver
    - user: lantern
    - group: lantern
    - mode: 755
    - makedirs: yes

# To filter through jinja.
{% set template_files=[
    ('/home/lantern/', 'util.py', 'util.py', 'lantern', 400),
    ('/home/lantern/', 'check_load.py', 'check_load.py', 'lantern', 700),
    ('/home/lantern/', 'check_traffic.py', 'check_traffic.py', 'lantern', 700),
    ('/home/lantern/', 'auth_token.txt', 'auth_token.txt', 'lantern', 400),
    ('/home/lantern/', 'fallback.json', 'fallback.json', 'lantern', 400),
    ('/opt/ts/libexec/trafficserver/', 'lantern-auth.so', 'lantern-auth.so', 'lantern', 700),
    ('/opt/ts/etc/trafficserver/', 'records.config', 'records.config', 'lantern', 400),
    ('/opt/ts/etc/trafficserver/', 'plugin.config', 'plugin.config', 'lantern', 400),
    ('/opt/ts/etc/trafficserver/', 'ssl_multicert.config', 'ssl_multicert.config', 'lantern', 400) ]%}

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

fallback-proxy-dirs-and-files:
    cmd.run:
        - name: ":"
        - require:
            {% for dir,dst_filename,src_filename,user,mode in template_files %}
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
            - cmd: generate-cert

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

install-ats:
    cmd.script:
        - source: salt://fallback_proxy/install_ats.sh
        - creates: /opt/ts/bin/traffic_cop
        - require:
            - cmd: fallback-proxy-dirs-and-files

convert-cert:
    cmd.script:
        - source: salt://fallback_proxy/convcert.sh
        - creates: /opt/ts/etc/trafficserver/key.pem
        - user: lantern
        - group: lantern
        - mode: 400
        - require:
            - cmd: generate-cert

ats-service:
    service.running:
        - name: trafficserver
        - enable: yes
        - reload: yes
        - watch:
            - cmd: ats-files
            - cmd: convert-cert
        - require:
            - pkg: tcl
            - cmd: ufw-rules-ready
