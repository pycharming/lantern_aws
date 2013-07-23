/etc/init.d/salt-master:
    file.managed:
        - user: root
        - group: root
        - source: salt://salt_master/salt-master.init
        - mode: 700

salt-master:
    service.running:
        - enable: yes
        - watch:
            - file: /etc/init.d/salt-master
