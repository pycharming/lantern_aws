include:
    - proxy_ufw_rules

{% set zone='cloudapp.net' %}
{% set domain_records_file='/home/lantern/cloudflare_records.yaml' %}


curl:
  pkg:
    - installed

/usr/bin/flashlight:
    file.absent
    
fl-installed:
    cmd.run:
        - name: 'curl -L -O https://github.com/getlantern/flashlight/releases/download/0.0.2/flashlight && chmod a+x flashlight'
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
