/etc/ufw/applications.d/borda:
    file.managed:
        - source: salt://borda_ufw_rules/ufw_rules
        - template: jinja
        - user: root
        - group: root
        - mode: 644

open-borda-port:
    cmd.run:
        - name: "ufw allow borda"
        - require:
            - file: /etc/ufw/applications.d/borda

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
            # Redirect port 62443 to borda
            -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 62443

            COMMIT

ufw-rules-ready:
    cmd.run:
        - name: 'service ufw restart'
        - user: root
        - group: root
        - require:
            - cmd: open-borda-port
        - watch:
            - file: /etc/ufw/applications.d/pubsub
            - file: /etc/default/ufw
            - file: /etc/ufw/sysctl.conf
            - file: /etc/ufw/before.rules
