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

maven:
    pkg.installed:
        - require:
            - pkg: oracle-java7-installer

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

lantern-repo:
    git.latest:
        - name: git://github.com/getlantern/lantern.git
        - rev: master
        - target: /home/lantern/repo
        - runas: lantern

# Chatty Maven makes salt logs unreadable.  I'm fine with just
# a success/failure indication for this step.
"/home/lantern/repo/install.bash > /dev/null":
    cmd.run:
        - user: lantern
        - group: lantern
        - cwd: /home/lantern/repo
        - require:
            - pkg: maven
        # XXX: this means any push to lantern master will get all EC2 instances
        # rebuilt!  In actual deployment we may want to manage a separate
        # branch for this instead.
        - watch:
            - git: lantern-repo
