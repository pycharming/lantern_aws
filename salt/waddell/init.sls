include:
    - proxy_ufw_rules

/usr/bin/waddell:
    file.absent

{% for name in 'waddell_pk.pem', 'waddell_cert.pem' %}
/home/lantern/{{ name }}:
    file.managed:
        - source: salt://waddell/{{ name }}
        - user: lantern
        - group: lantern
        - mode: 600
{% endfor %} 
    
waddell-installed:
    cmd.run:
        - name: 'curl -L https://github.com/getlantern/flashlight-build/releases/download/0.0.4/waddell_linux_amd64 -o waddell && chmod a+x waddell'
        - cwd: '/usr/bin'
        - user: root

waddell-upstart-script:
    file.managed:
        - name: /etc/init/waddell.conf
        - source: salt://waddell/waddell.conf
        - template: jinja
        - user: root
        - group: root
        - mode: 644
        - require:
            - cmd: waddell-installed

waddell-service-registered:
    cmd.run:
        - name: 'initctl reload-configuration'
        - watch:
            - file: waddell-upstart-script

waddell:
    service.running:
        - enable: yes
        - require:
            # All but the last requirement are redundant, only for robustness.
            - cmd: ufw-rules-ready
            - cmd: waddell-installed
            - cmd: waddell-service-registered
            - file: /home/lantern/waddell_pk.pem
            - file: /home/lantern/waddell_cert.pem
        - watch:
            - file: /usr/bin/waddell