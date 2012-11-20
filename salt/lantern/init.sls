lantern:
    user.present:
        - home: /home/lantern
        - shell: /bin/bash

/home/lantern:
    file.directory:
        - user: lantern
        - group: lantern
        - mode: 700
        - require:
            - user: lantern

/home/lantern/repo:
    file.directory:
        - user: lantern
        - group: salt
        - mode: 700
        - require:
            - file: /home/lantern

# I have created this on bootstrap; manage owner and permissions.
/etc/lantern:
    file.directory:
        - user: lantern
        - group: lantern
        - mode: 700
        - require:
            - user: lantern

# I have created this on bootstrap; manage owner and permissions.
/etc/lantern/public-proxy-port:
    file.managed:
        - replace: no
        - user: lantern
        - group: lantern
        - mode: 600
        - require:
            - file: /etc/lantern

git://github.com/getlantern/lantern.git:
    git.latest:
        - rev: master
        - target: /home/lantern/repo
        - runas: lantern

