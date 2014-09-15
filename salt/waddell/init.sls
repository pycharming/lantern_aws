include:
    - proxy_ufw_rules

curl:
  pkg:
    - installed

/usr/bin/waddell:
    file.absent
    
waddell-installed:
    cmd.run:
        - name: 'curl -L -O https://github.com/getlantern/waddell/releases/download/0.0.1/waddell && chmod a+x waddell'
        - cwd: '/usr/bin'
        - user: root
        - require:
          - pkg: curl

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
        - watch:
            - file: /usr/bin/waddell