lantern:
    user.present:
        - home: /home/lantern
        - shell: /bin/bash

java-repo:
    apt_repository.ubuntu_ppa:
        - user: webupd8team
        - name: java
        - key_id: EEA14886

apt-update:
    cmd.wait:
        - name: "apt-get --assume-yes update"
        - user: root
        - stateful: no
        - watch:
            - apt_repository: java-repo

accept-oracle-license:
    cmd.run:
        - name: "echo oracle-java7-installer shared/accepted-oracle-license-v1-1 select true | /usr/bin/debconf-set-selections"
        - user: root

oracle-java7-installer:
    pkg.installed:
        - require:
            - cmd: apt-update
            - cmd: accept-oracle-license

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

