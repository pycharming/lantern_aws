include:
    - proxy_ufw_rules


#XXX: make your service require this instead:
":":
    cmd.run:
        - require:
            - cmd: ufw-rules-ready

curl:
  pkg:
    - installed

mailutils:
  pkg:
    - installed

monitor-script:
    file.managed:
        - name: /home/lantern/monitor.bash
        - source: salt://flashlight/monitor.bash
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: 744
        - require:
            - pkg: mailutils
            - pkg: curl

# XXX: uncomment when we have a service to monitor.
#monitor:
#    cron.present:
#        - name: /home/lantern/monitor.bash flashlight
#        - minute: '*/15'
#        - user: lantern
#        - require:
#            - file: /home/lantern/monitor.bash
#            - service: flashlight
