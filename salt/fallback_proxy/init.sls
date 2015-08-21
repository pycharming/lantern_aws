{% set fallback_json_file='/home/lantern/fallback.json' %}
{% set proxy_protocol=pillar.get('proxy_protocol', 'tcp') %}
{% set auth_token=pillar.get('auth_token') %}
{% set proxy_port=grains.get('proxy_port', 62443) %}
{% set traffic_check_period_minutes=60 %}
{% from 'ip.sls' import external_ip %}

{% set lantern_args = "-Xmx350m org.lantern.simple.Give "
                    + "-instanceid " + pillar['instance_id']
                    + " -host 127.0.0.1 "
                    + " -http " + (proxy_port - 443)|string
                    + " -https " + proxy_port|string
                    + " -keystore /home/lantern/littleproxy_keystore.jks "
                    + " -authtoken " + auth_token %}

# To filter through jinja.
{% set template_files=[
    ('/etc/init.d/', 'lantern', 'lantern.init', 'root', 700),
    ('/home/lantern/', 'check_lantern.py', 'check_lantern.py', 'root', 700),
    ('/home/lantern/', 'util.py', 'util.py', 'lantern', 400),
    ('/home/lantern/', 'check_load.py', 'check_load.py', 'lantern', 700),
    ('/home/lantern/', 'check_traffic.py', 'check_traffic.py', 'lantern', 700),
    ('/home/lantern/', 'kill_lantern.py', 'kill_lantern.py', 'lantern', 700),
    ('/home/lantern/', 'report_stats.py', 'report_stats.py', 'lantern', 700),
    ('/home/lantern/', 'auth_token.txt', 'auth_token.txt', 'lantern', 400),
    ('/home/lantern/', 'fallback.json', 'fallback.json', 'lantern', 400),
    ('/home/lantern/', 'fte.props', 'fte.props', 'lantern', 400)] %}

{% set lantern_pid='/var/run/lantern.pid' %}

include:
    - boto
    - lantern
    - proxy_ufw_rules

/home/lantern/secure:
    file.directory:
        - user: lantern
        - group: lantern
        - mode: 500

{% for dir,dst_filename,src_filename,user,mode in template_files %}
{{ dir+dst_filename }}:
    file.managed:
        - source: salt://fallback_proxy/{{ src_filename }}
        - template: jinja
        - context:
            lantern_args: {{ lantern_args }}
            lantern_pid: {{ lantern_pid }}
            proxy_protocol: {{ proxy_protocol }}
            auth_token: {{ auth_token }}
            external_ip: {{ external_ip(grains) }}
            traffic_check_period_minutes: {{ traffic_check_period_minutes }}
        - user: {{ user }}
        - group: {{ user }}
        - mode: {{ mode }}
{% endfor %}


fallback-proxy-dirs-and-files:
    cmd.run:
        - name: ":"
        - require:
            - file: /home/lantern/secure
            - file: /etc/init.d/lantern
            {% for dir,dst_filename,src_filename,user,mode in template_files %}
            - file: {{ dir+dst_filename }}
            {% endfor %}

lantern-service:
    service.running:
        - name: lantern
        - enable: yes
        - require:
            - cmd: ufw-rules-ready
            - cmd: fallback-proxy-dirs-and-files
        - watch:
            - cmd: install-lantern
            - file: /etc/init.d/lantern

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
            - service: lantern-service
            # I need boto updated so I have the same version as the cloudmaster
            # and thus I can unpickle and delete the SQS message that
            # triggered the launching of this instance.
            - pip: boto==2.9.5
            - file: {{ fallback_json_file }}
            - cmd: generate-cert

zip:
    pkg.installed

python-dev:
    pkg.installed

build-essential:
    pkg.installed

psutil:
    pip.installed:
        - name: psutil==2.1.1
        - require:
            - pkg: build-essential
            - pkg: python-dev

requests:
  pip.installed

report-stats:
    cron.present:
        - name: /home/lantern/report_stats.py
        - minute: '*/11'
        - user: lantern
        - require:
            - file: /home/lantern/report_stats.py
            - pip: psutil
            - service: lantern


{% if pillar['in_production'] %}

check-lantern:
    cron.present:
        - name: /home/lantern/check_lantern.py
        - user: root
        - minute: '*/1'
        - require:
            - file: /home/lantern/check_lantern.py
            - pip: psutil
            - service: lantern

"/home/lantern/check_load.py 2>&1 | logger -t check_load":
  cron.present:
    - minute: "*/7"
    - user: lantern
    - require:
        - file: /home/lantern/check_load.py
        - pip: requests

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

# bug: missing -t
"/home/lantern/check_vultr_transfer.py | logger check_vultr_transfer":
  cron.absent:
    - user: lantern

# bug: missing 2>&1
"/home/lantern/check_vultr_transfer.py | logger -t check_vultr_transfer":
  cron.absent:
    - user: lantern

"/home/lantern/check_vultr_transfer.py 2>&1 | logger -t check_vultr_transfer":
  cron.present:
    - identifier: check_vultr_transfer
    - minute: random
    - user: lantern
    - require:
        - file: /home/lantern/check_vultr_transfer.py
        - pip: vultr

{% endif %}

{% endif %}


# Dictionary of American English words for the dname generator in
# generate-cert.
wamerican:
    pkg.installed

generate-cert:
    cmd.script:
        - source: salt://fallback_proxy/gencert.py
        - template: jinja
        # Don't clobber the keystore of old fallbacks.
        - unless: '[ -e /home/lantern/littleproxy_keystore.jks ]'
        - require:
            - pkg: wamerican
