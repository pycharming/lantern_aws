# Note that lantern user and home directory have been created in
# lantern_administrators.

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
        - rev: oauth2
        - target: /home/lantern/repo
        - runas: lantern
        - require:
            - file: /home/lantern/repo

generate-password-file:
    cmd.run:
        - name: "dd if=/dev/urandom bs=12 count=1 | base64 > /home/lantern/password"
        - user: lantern
        - unless: "test -f /home/lantern/password"
        - require:
            - file: /home/lantern

# Chatty Maven makes salt logs unreadable.  I'm fine with just
# a success/failure indication for this step.
build-lantern:
    cmd.run:
        # Make sure we only ever build once.
        - name: "if (umask 222; echo x > ../.started-building-lantern) ./install.bash > /dev/null; fi"
        - user: lantern
        - group: lantern
        - cwd: /home/lantern/repo
        - require:
            - pkg: maven
            - git: lantern-repo

init-script:
    file.managed:
        - name: /etc/init.d/lantern
        - user: root
        - group: root
        - mode: 700
        - source: salt://lantern/init-script

lantern-service:
    service.running:
        - requires:
            - file: init-script
            - cmd: build-lantern
            - cmd: generate-password-file
