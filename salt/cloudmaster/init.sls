include:
    - cloudmaster.installer_prereqs


/home/lantern/cloudmaster.py:
    file.managed:
        - source: salt://cloudmaster/cloudmaster.py
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: 700

/etc/init.d/cloudmaster:
    file.managed:
        - source: salt://cloudmaster/cloudmaster.init
        - user: root
        - mode: 700

cloudmaster-service:
    service.running:
        - name: cloudmaster
        - enabled: yes
        - require:
            - file: /home/lantern/cloudmaster.py
            - file: /etc/init.d/cloudmaster
            - cmd: installer-prereqs
