include:
    - proxy_ufw_rules

{% set zone='getiantem.org' %}
{% set domain_records_file='/home/lantern/cloudflare_records.yaml' %}


fl-installed:
    cmd.run:
        - unless: 'which flashlight'
        - name: 'wget -qct 3 https://s3.amazonaws.com/lantern-aws/flashlight && chmod a+x flashlight'
        - cwd: '/usr/bin'
        - user: root

fl-upstart-script:
    file.managed:
        - name: /etc/init/flashlight.conf
        - source: salt://flashlight/flashlight.conf
        - template: jinja
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

pyflare:
    pip.installed:
        - name: pyflare==1.0.2
        - upgrade: yes

/home/lantern/register_domains.py:
    file.managed:
        - source: salt://flashlight/register_domains.py
        - template: jinja
        - context:
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
