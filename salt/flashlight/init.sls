include:
    - proxy_ufw_rules

{% set zone='getiantem.org' %}
{% if grains.get('provider', 'unknown') == 'azure' %}
{% set server=pillar.get('cdn', 'UNKNOWN_CDN') %}
{% else %}
{% set server = grains['id'] + "." + zone %}
{% endif %}
{% set domain_records_file='/home/lantern/cloudflare_records.yaml' %}


curl:
  pkg:
    - installed

mailutils:
  pkg:
    - installed

/usr/bin/flashlight:
    file.absent
    
fl-installed:
    cmd.run:
        - name: 'curl -L https://github.com/getlantern/flashlight-build/releases/download/0.0.6/flashlight_linux_amd64 -o flashlight && chmod a+x flashlight'
        - cwd: '/usr/bin'
        - user: root
        - require:
          - pkg: curl

sudo /sbin/restart flashlight 2>&1 | logger -t flashlight_restarter:
    cron.absent:
        - identifier: flashlight-cron-restart
        - user: lantern

fl-upstart-script:
    file.managed:
        - name: /etc/init/flashlight.conf
        - source: salt://flashlight/flashlight.conf
        - template: jinja
        - context:
            server: {{ server }}
        - user: root
        - group: root
        - mode: 644
        - require:
            - cmd: fl-installed

fl-service-registered:
    cmd.run:
        - name: 'initctl reload-configuration'
        - watch:
            - file: fl-upstart-script

flashlight:
    service.running:
        - enable: yes
        - require:
            # All but the last requirement are redundant, only for robustness.
            - cmd: ufw-rules-ready
            - cmd: fl-installed
            - cmd: fl-service-registered
        - watch:
            - file: /usr/bin/flashlight

monitor-script:
    file.managed:
        - name: /home/lantern/monitor.bash
        - source: salt://flashlight/monitor.bash
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: 744
        - require:
            - pkg: mailutils
            - pkg: curl

monitor:
    cron.present:
        - name: /home/lantern/monitor.bash
        - minute: '*/15'
        - user: lantern
        - require:
            - file: /home/lantern/monitor.bash
            - service: flashlight

{% if grains.get('provider', 'unknown') != 'azure' %}

pyflare:
    pip.installed:
        - name: pyflare==1.0.2
        - upgrade: yes

/home/lantern/register_domains.py:
    file.managed:
        - source: salt://flashlight/register_domains.py
        - template: jinja
        - context:
            zone: {{ zone }}
            domain_records_file: {{ domain_records_file }}
        - user: lantern
        - group: lantern
        - mode: 700

register-domains:
    cmd.run:
        - name: "/home/lantern/register_domains.py"
        - unless: "[ -e {{ domain_records_file }} ]"
        - user: lantern
        - group: lantern
        - cwd: /home/lantern
        - require:
            - pip: pyflare
            - service: flashlight
            - file: /home/lantern/register_domains.py
{% endif %}
