include:
    - proxy_ufw_rules

{% from 'install_from_release.sls' import install_from_release %}

{# define cmd: peerscanner-installed #}
{{ install_from_release('peerscanner', '0.0.16') }}

ps-upstart-script:
    file.managed:
        - name: /etc/init/peerscanner.conf
        - source: salt://peerscanner/peerscanner.conf
        - template: jinja
        - user: root
        - group: root
        - mode: 644
        - require:
            - cmd: peerscanner-installed

ps-service-registered:
    cmd.run:
        - name: 'initctl reload-configuration'
        - watch:
            - file: ps-upstart-script

{# Don't automatically start the server in test setups. #}
{% if pillar['in_production'] %}
peerscanner:
    service.running:
        - enable: yes
        - require:
            - cmd: ufw-rules-ready
            - cmd: ps-service-registered
        - watch:
            - cmd: peerscanner-installed

monitor-script:
    file.managed:
        - name: /home/lantern/monitor.bash
        - source: salt://flashlight/monitor.bash
        - user: lantern
        - group: lantern
        - mode: 744

monitor:
    cron.present:
        - name: /home/lantern/monitor.bash peerscanner
        - minute: '*/15'
        - user: lantern
        - require:
            - file: /home/lantern/monitor.bash
            - service: peerscanner
{% endif %}
