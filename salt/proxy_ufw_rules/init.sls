{% set proxy_protocol=pillar.get('proxy_protocol', 'tcp') %}
{% set proxy_port=pillar.get('proxy_port', 443) %}

/etc/ufw/applications.d/lantern:
    file.managed:
        - source: salt://proxy_ufw_rules/ufw_rules
        - template: jinja
        - context:
            proxy_port: {{ proxy_port }}
            proxy_protocol: {{ proxy_protocol }}
        - user: root
        - group: root
        - mode: 644

open-proxy-port:
    cmd.run:
        - name: "ufw allow lantern_proxy"
        - require:
            - file: /etc/ufw/applications.d/lantern

/etc/default/ufw:
    file.replace:
        - pattern: '^DEFAULT_FORWARD_POLICY="DROP"$'
        - repl:     'DEFAULT_FORWARD_POLICY="ACCEPT"'

/etc/ufw/sysctl.conf:
    file.append:
        - text: |
            net/ipv4/ip_forward=1
            net/ipv6/conf/default/forwarding=1

{% if proxy_protocol == 'tcp' %}
/etc/ufw/before.rules:
    file.replace:
        - pattern: \*nat.+COMMIT
        - flags: ['MULTILINE', 'DOTALL']
        - repl: ''
{% endif %}


ufw-update-lantern:
  cmd.run:
    - name: ufw app update lantern_proxy
    - watch:
      - file: /etc/ufw/applications.d/lantern

ufw-rules-ready:
    cmd.run:
        - name: 'service ufw restart'
        - user: root
        - group: root
        - require:
            - cmd: open-proxy-port
            - cmd: ufw-update-lantern
        - watch:
            - file: /etc/ufw/applications.d/lantern
            - file: /etc/default/ufw
            - file: /etc/ufw/sysctl.conf
{% if proxy_protocol == 'tcp' %}
            - file: /etc/ufw/before.rules
{% endif %}
