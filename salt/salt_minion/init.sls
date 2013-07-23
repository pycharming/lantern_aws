/etc/init.d/salt-minion:
    file.managed:
        - user: root
        - group: root
        - source: salt://salt_minion/salt-minion.init
        - mode: 700

salt-minion:
    service.running:
        - enable: yes
        - watch:
            - file: /etc/init.d/salt-minion
