include:
    - go

{% from 'go/init.sls' import GOPATH %}

fl-installed:
    cmd.run:
        - unless: 'which flashlight'
        - name: 'go get github.com/getlantern/flashlight'
        - user: lantern

fl-upstart-script:
    file.managed:
        - name: /etc/init/flashlight.conf
        - source: salt://flashlight/flashlight.conf
        - template: jinja
        - context:
            GOPATH: {{ GOPATH }}
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
