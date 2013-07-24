include:
    - salt_minion

/etc/init.d/salt-master:
    file.managed:
        - user: root
        - group: root
        - source: salt://salt_master/salt-master.init
        - mode: 700

salt-master:
    # Remove apt package so we don't upgrade automatically.
    # We get salt-master through the 'salt' pip package, which we install in
    # salt-minion.
    pkg.removed: []
    service.running:
        - enable: yes
        - watch:
            - file: /etc/init.d/salt-master
            - pip: salt
