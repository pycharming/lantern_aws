include:
    - salt_cloud

/etc/ufw/applications.d/salt:
    file.managed:
        - source: salt://cloudmaster/ufw-rules
        - user: root
        - group: root
        - mode: 644

'ufw app update Salt ; ufw allow salt':
    cmd.run:
        - require:
            - file: /etc/ufw/applications.d/salt

/home/lantern/cloudmaster.py:
    file.managed:
        - source: salt://cloudmaster/cloudmaster.py
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: 700
    cron.present:
        - user: lantern
        - require:
            - pip: lockfile==0.9.1
            - pip: salt-cloud

lockfile==0.9.1:
    pip.installed
