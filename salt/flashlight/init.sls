include:
    - proxy_ufw_rules

{% set zone='getiantem.org' %}
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
        - name: 'curl -L https://github.com/getlantern/flashlight-build/releases/download/0.0.9/flashlight_linux_amd64 -o flashlight && chmod a+x flashlight'
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
            zone: {{ zone }}
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
        - name: /home/lantern/monitor.bash flashlight
        - minute: '*/15'
        - user: lantern
        - require:
            - file: /home/lantern/monitor.bash
            - service: flashlight
