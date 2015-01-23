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
        - name: 'curl -L https://github.com/getlantern/flashlight-build/releases/download/0.0.9/peerscanner_linux_amd64 -o peerscanner && chmod a+x peerscanner'
        - cwd: '/usr/bin'
        - user: root
        - require:
          - pkg: curl
          - file: /usr/bin/peerscanner

ps-upstart-script:
    file.managed:
        - name: /etc/init/peerscanner.conf
        - source: salt://peerscanner/peerscanner.conf
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
            - cmd: ps-installed
            - cmd: ps-service-registered
        - watch:
            - file: /usr/bin/peerscanner

monitor-script:
    file.managed:
        - name: /home/lantern/monitor.bash
        - source: salt://flashlight/monitor.bash
        - user: lantern
        - group: lantern
        - mode: 744
        - require:
            - pkg: mailutils
            - pkg: curl

monitor:
    cron.present:
        - name: /home/lantern/monitor.bash peerscanner
        - minute: '*/15'
        - user: lantern
        - require:
            - file: /home/lantern/monitor.bash
            - service: peerscanner
