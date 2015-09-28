java-ppa:
  pkgrepo.managed:
    - ppa: webupd8team/java

java-home:
    file.append:
        - name: /etc/profile
        - text: "export JAVA_HOME=/usr/lib/jvm/java-7-oracle"

accept-oracle-terms:
    cmd.run:
        - name: "echo oracle-java7-installer shared/accepted-oracle-license-v1-1 select true | /usr/bin/debconf-set-selections"
        - user: root

java:
    pkg.installed:
        - order: 2
        - names:
            - oracle-java7-installer
            - oracle-java7-set-default
        - require:
            - pkgrepo: java-ppa
            - file: java-home
            - cmd: accept-oracle-terms
    cmd.run:
        - order: 2
        - name: "update-java-alternatives -s java-7-oracle"
        - user: root
        - require:
            - pkg: java

#XXX: is this still necessary?
{% set maven_version='3.1.1' %}
maven:
    cmd.script:
        - order: 2
        - source: salt://lantern_build_prereqs/install-maven.bash
        - template: jinja
        - context:
            maven_version: {{ maven_version }}
        - unless: "[ -e  /usr/local/apache-maven-{{ maven_version }}/bin/mvn ] "
        - user: root
        - cwd: /tmp
