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

# I have created this on bootstrap; manage owner and permissions.
/etc/lantern:
    file.directory:
        - user: lantern
        - group: lantern
        - mode: 700
        - require:
            - user: lantern

/home/lantern/installers-repo:
    file.directory:
        - user: lantern
        - group: lantern
        - mode: 700
        - require:
            - file: /home/lantern

installers-repo:
    git.latest:
        - name: git://github.com/getlantern/lantern.git
        - rev: aws_installer
        - target: /home/lantern/installers-repo
        - runas: lantern
        - require:
            - file: /home/lantern/installers-repo

/root/install4j_linux_5_1_3.deb:
    file.managed:
        - source: http://download-aws.ej-technologies.com/install4j/install4j_linux_5_1_3.deb

install4j:
    cmd.run:
        - name: "dpkg -i /root/install4j_linux_5_1_3.deb":
        - unless: "which install4jc > /dev/null"
        - user: root
        - group: root
        - requires:
            - file: /root/install4j_linux_5_1_3.deb

windows-jre:
    file.managed:
        - name: "/home/lantern/installers-repo/windows-x86-1.7.0_03.tar.gz"
        - source: http://cdn.getlantern.org/windows-x86-1.7.0_03.tar.gz
        - user: lantern
        - group: lantern
        - mode: 400

/home/lantern/build-installers.bash:
    file.managed:
        - source: salt://lantern/build-installers.bash
        - user: lantern
        - group: lantern
        - mode: 700
    cmd.run:
        - name: /home/lantern/build-installers.bash
        - user: lantern
        - group: lantern
        - cwd: /home/lantern/installers-repo
        - require:
            - file: /home/lantern/build-installers.bash
            - git: installers-repo
            - cmd: install4j
            - file: windows-jre

# Copy repo after first build to avoid downloading and building twice.
copy-repo:
    cmd.run:
        - name: "cp -r /home/lantern/installers-repo /home/lantern/run-repo"
        - user: lantern
        - unless: "test -f /home/lantern/installers-repo"
        - require:
            - cmd: /home/lantern/build-installers.bash

run-repo:
    git.latest:
        - name: git://github.com/getlantern/lantern.git
        - rev: oauth2
        - target: /home/lantern/run-repo
        - runas: lantern
        - require:
            - cmd: copy-repo

# Chatty Maven makes salt logs unreadable.  I'm fine with just
# a success/failure indication for this step.
build-lantern:
    cmd.run:
        # Make sure we only ever build once.
        - name: "if (umask 222; echo x > ../.started-building-lantern) 2> /dev/null; then ./install.bash > /dev/null; fi"
        - user: lantern
        - group: lantern
        - cwd: /home/lantern/run-repo
        - require:
            - pkg: maven
            - git: run-repo

generate-password-file:
    cmd.run:
        - name: "dd if=/dev/urandom bs=12 count=1 | base64 > /home/lantern/password"
        - user: lantern
        - unless: "test -f /home/lantern/password"
        - require:
            - file: /home/lantern

init-script:
    file.managed:
        - name: /etc/init.d/lantern
        - user: root
        - group: root
        - mode: 700
        - source: salt://lantern/init-script

lantern-service:
    service.running:
        - name: lantern
        - requires:
            - file: init-script
            - cmd: build-lantern
            - cmd: generate-password-file
