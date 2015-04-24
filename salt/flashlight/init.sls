include:
    - proxy_ufw_rules

{% set zone='getiantem.org' %}
{% set frontfqdns = "{cloudflare: " + grains['id'] + "." + zone + "}" %}
{% if grains.get('controller', pillar.get('controller', 'not-production')) == grains.get('production_controller', 'lanternctrl1-2') %}
{% set registerat="-registerat https://peerscanner." + zone %}
{% else %}
{% set registerat="" %}
{% endif %}

/usr/bin/flashlight:
    file.absent
    
fl-installed:
    cmd.run:
        - name: 'curl -L https://github.com/getlantern/lantern/releases/download/0.0.17/lantern_linux_amd64 -o flashlight && chmod a+x flashlight'
        - cwd: '/usr/bin'
        - user: root
        - require:
          - file: /usr/bin/flashlight

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
            frontfqdns: {{ frontfqdns }}
            registerat: {{ registerat | python }}
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
            - cmd: ufw-rules-ready
            - cmd: fl-service-registered
            - pkg: libappindicator3-1
        - watch:
            - file: /usr/bin/flashlight
            - cmd: fl-installed

monitor-script:
    file.managed:
        - name: /home/lantern/monitor.bash
        - source: salt://flashlight/monitor.bash
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: 744

monitor:
    cron.present:
        - name: /home/lantern/monitor.bash flashlight
        - minute: '*/15'
        - user: lantern
        - require:
            - file: /home/lantern/monitor.bash
            - service: flashlight
