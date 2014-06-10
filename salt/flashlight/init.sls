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
            - cmd: ufw-forwarding-ready

fl-service-registered:
    cmd.run:
        - name: 'initctl reload-configuration'
        - watch:
            - file: fl-upstart-script

/etc/default/ufw:
    file.replace:
        - pattern: '^DEFAULT_FORWARD_POLICY="DROP"$'
        - repl:     'DEFAULT_FORWARD_POLICY="ACCEPT"'

/etc/ufw/sysctl.conf:
    file.append:
        - text: |
            net/ipv4/ip_forward=1
            net/ipv6/conf/default/forwarding=1

/etc/ufw/before.rules:
    file.append:
        - text: |
            *nat

            :PREROUTING ACCEPT - [0:0]
            # Redirect ports 80 and 443 to the Lantern proxy
            #-A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 62000
            -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 62443

            COMMIT

ufw-forwarding-ready:
    cmd.run:
        - name: 'service ufw restart'
        - user: root
        - group: root
        - watch:
            - file: /etc/default/ufw
            - file: /etc/ufw/sysctl.conf
            - file: /etc/ufw/before.rules

flashlight:
    service.running:
        - enable: yes
        - require:
            # All but the last requirement are redundant, only for robustness.
            - cmd: ufw-forwarding-ready
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
