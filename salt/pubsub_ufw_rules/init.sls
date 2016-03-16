{% set proxy_protocol=pillar.get('proxy_protocol', 'tcp') %}

/etc/ufw/applications.d/pubsub:
    file.managed:
        - source: salt://pubsub_ufw_rules/ufw_rules
        - template: jinja
        - context:
            proxy_protocol: {{ proxy_protocol }}
        - user: root
        - group: root
        - mode: 644

open-proxy-port:
    cmd.run:
        - name: "ufw allow pubsub"
        - require:
            - file: /etc/ufw/applications.d/pubsub

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
            # Redirect ports 14443 and 62443 to the broker
            -A PREROUTING -p tcp --dport 14443 -j REDIRECT --to-port 14443
            -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 62443

            COMMIT

ufw-rules-ready:
    cmd.run:
        - name: 'service ufw restart'
        - user: root
        - group: root
        - require:
            - cmd: open-proxy-port
        - watch:
            - file: /etc/ufw/applications.d/pubsub
            - file: /etc/default/ufw
            - file: /etc/ufw/sysctl.conf
            - file: /etc/ufw/before.rules
