include:
    - salt_cloud
    - lockfile

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
        - user: root
        - group: root
        - mode: 700
    cron.present:
        - user: root
        - minute: "*/1"
        - require:
            - pip: lockfile

/usr/bin/regenerate-fallbacks-list:
    file.managed:
        - source: salt://cloudmaster/regenerate_fallbacks_list.py
        - user: root
        - group: root
        - mode: 700

/usr/bin/accept-minions:
    file.managed:
        - source: salt://cloudmaster/accept_minions.py
        - user: root
        - group: root
        - mode: 700

/home/lantern/.ssh:
    file.directory:
        - user: lantern
        - gid: lantern
        - mode: 700

/home/lantern/.ssh/id_rsa:
    file.managed:
        - source: salt://cloudmaster/id_rsa
        - user: lantern
        - mode: 400
        - require:
            - file: /home/lantern/.ssh

/home/lantern/.ssh/id_rsa.pub:
    file.managed:
        - source: salt://cloudmaster/id_rsa.pub
        - user: lantern
        - mode: 400
        - require:
            - file: /home/lantern/.ssh