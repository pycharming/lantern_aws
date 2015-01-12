/etc/salt/master:
    file.managed:
        - user: root
        - group: root
        - source: salt://salt_master/config
        - mode: 600

salt-master:
    service.running:
        - enable: yes
        - watch:
            - file: /etc/salt/master
