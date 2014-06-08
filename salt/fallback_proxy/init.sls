{% set access_data_file='/home/lantern/fallback.json' %}
{% set proxy_protocol=pillar.get('proxy_protocol', 'tcp') %}
{% set auth_token=pillar.get('auth_token') %}
#XXX: hotfix; do a proper grain to fetch public IP.
{% if grains['ipv4'][0] == '127.0.0.1' %}
    {% set public_ip=(grains.get('ec2-public_ipv4') or grains['ipv4'][1]) %}
{% else %}
    {% set public_ip=(grains.get('ec2-public_ipv4') or grains['ipv4'][0]) %}
{% endif %}

{% set lantern_args = "-Xmx350m org.lantern.simple.Give "
                    + "-instanceid " + pillar['instance_id']
                    + " -host 127.0.0.1 "
                    + " -http " + (grains['proxy_port'] - 443)|string
                    + " -https " + (grains['proxy_port'])|string
                    + " -keystore /home/lantern/littleproxy_keystore.jks "
                    + " -authtoken " + auth_token %}

# To filter through jinja.
{% set template_files=[
    ('/etc/ufw/applications.d/', 'lantern', 'ufw_rules', 'root', 644),
    ('/etc/init.d/', 'lantern', 'lantern.init', 'root', 700),
    ('/home/lantern/', 'check_lantern.py', 'check_lantern.py', 'root', 700),
    ('/home/lantern/', 'kill_lantern.py', 'kill_lantern.py', 'lantern', 700),
    ('/home/lantern/', 'report_stats.py', 'report_stats.py', 'lantern', 700),
    ('/home/lantern/', 'auth_token.txt', 'auth_token.txt', 'lantern', 400),
    ('/home/lantern/', 'fallback.json', 'fallback.json', 'lantern', 400),
    ('/home/lantern/', 'fte.props', 'fte.props', 'lantern', 400)] %}

{% set lantern_pid='/var/run/lantern.pid' %}

include:
    - boto
    - lantern

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
            public_ip: {{ public_ip }}
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
            - file: /etc/ufw/applications.d/lantern
            {% for dir,dst_filename,src_filename,user,mode in template_files %}
            - file: {{ dir+dst_filename }}
            {% endfor %}

open-proxy-port:
    cmd.run:
        - name: "ufw allow lantern_proxy"
        - require:
            - cmd: fallback-proxy-dirs-and-files

lantern-service:
    service.running:
        - name: lantern
        - enable: yes
        - require:
            - cmd: open-proxy-port
            - cmd: fallback-proxy-dirs-and-files
        - watch:
            # Restart when we get a new user to run as, or a new refresh token.
            - cmd: install-lantern
            - file: /etc/init.d/lantern

report-completion:
    cmd.script:
        - source: salt://fallback_proxy/report_completion.py
        - template: jinja
        - context:
            public_ip: {{ public_ip }}
            access_data_file: {{ access_data_file }}
        - unless: "[ -e /home/lantern/reported_completion ]"
        - user: lantern
        - group: lantern
        - cwd: /home/lantern
        - require:
            - service: lantern-service
            # I need boto updated so I have the same version as the cloudmaster
            # and thus I can unpickle and delete the SQS message that
            # triggered the launching of this instance.
            - pip: boto==2.9.5
            - file: {{ access_data_file }}
            - cmd: generate-cert

zip:
    pkg.installed

python-dev:
    pkg.installed

build-essential:
    pkg.installed

psutil:
    pip.installed:
        - name: psutil==2.1.0
        - require:
            - pkg: build-essential
            - pkg: python-dev

report-stats:
    cron.present:
        - name: /home/lantern/report_stats.py
        - minute: '*/10'
        - user: lantern
        - require:
            - file: /home/lantern/report_stats.py
            - pip: psutil
            - service: lantern

{% if grains['controller'] == grains.get('production_controller', 'lanternctrl1-2') %}
check-lantern:
    cron.present:
        - name: /home/lantern/check_lantern.py
        - user: root
        - minute: '*/1'
        - require:
            - file: /home/lantern/check_lantern.py
            - pip: psutil
            - service: lantern
{% endif %}

/etc/default/ufw:
    file.replace:
        - pattern: '^DEFAULT_FORWARD_POLICY="DROP"$'
        - repl:     'DEFAULT_FORWARD_POLICY="ACCEPT"'

/etc/ufw/sysctl.conf:
    file.append:
        - text: |
            net/ipv4/ip_forward=1
            net/ipv6/conf/default/forwarding=1

{% if proxy_protocol == 'tcp' %}
/etc/ufw/before.rules:
    file.append:
        - text: |
            *nat

            :PREROUTING ACCEPT - [0:0]
            # Redirect ports 80 and 443 to the Lantern proxy
            -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 62000
            -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 62443

            COMMIT

{% endif %}

restart-ufw:
    cmd.run:
        - name: 'service ufw restart'
        - user: root
        - group: root

# Dictionary of American English words for the dname generator in
# generate-cert.
wamerican:
    pkg.installed

generate-cert:
    cmd.script:
        - source: salt://fallback_proxy/gencert.py
        # Don't clobber the keystore of old fallbacks.
        - unless: '[ -e /home/lantern/littleproxy_keystore.jks ]'
        - require:
            - pkg: wamerican
