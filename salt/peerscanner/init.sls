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

/usr/bin/peerscanner:
    file.absent
    
ps-installed:
    cmd.run:
        - name: 'curl -L https://github.com/getlantern/flashlight-build/releases/download/0.0.8/peerscanner_linux_amd64 -o peerscanner && chmod a+x peerscanner'
        - cwd: '/usr/bin'
        - user: root
        - require:
          - pkg: curl

ps-upstart-script:
    file.managed:
        - name: /etc/init/peerscanner.conf
        - source: salt://peerscanner/peerscanner.conf
        - template: jinja
        - context:
            zone: {{ zone }}
        - user: root
        - group: root
        - mode: 644
        - require:
            - cmd: ps-installed

ps-service-registered:
    cmd.run:
        - name: 'initctl reload-configuration'
        - watch:
            - file: ps-upstart-script

peerscanner:
    service.running:
        - enable: yes
        - require:
            # All but the last requirement are redundant, only for robustness.
            - cmd: ufw-rules-ready
            - cmd: ps-installed
            - cmd: ps-service-registered
        - watch:
            - file: /usr/bin/peerscanner