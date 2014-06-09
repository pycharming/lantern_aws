include:
    - go

{% set FL_PID='/var/run/flashlight.pid' %}
{% from 'go/init.sls' import GOPATH %}

install-fl:
    cmd.run:
        - unless: 'which flashlight'
        - name: 'go get github.com/getlantern/flashlight'
        - user: lantern

fl-init-script:
    file.managed:
        - name: /etc/init.d/flashlight
        - source: salt://flashlight/flashlight.init
        - template: jinja
        - context:
            GOPATH: {{ GOPATH }}
            FL_PID: {{ FL_PID }}
        - user: root
        - group: root
        - mode: 700

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
            - cmd: install-fl
            - cmd: ufw-forwarding-ready
