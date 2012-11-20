lantern:
    user.present:
        - home: /home/lantern
        - shell: /bin/bash

/home/lantern:
    - user: lantern
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
        - mode: 700
        - recurse: yes
        - require:
            - user: lantern

git://github.com/getlantern/lantern.git:
    git.latest:
        - rev: master
        - target: /home/lantern/repo
        - runas: lantern

