{% if pillar.get('install-from') == 'git' %}

java-ppa:
  pkgrepo.managed:
    - ppa: webupd8team/java

java-home:
    file.append:
        - name: /etc/profile
        - text: "export JAVA_HOME=/usr/lib/jvm/java-8-oracle"

accept-oracle-terms:
    cmd.run:
        - name: "echo oracle-java8-installer shared/accepted-oracle-license-v1-1 select true | /usr/bin/debconf-set-selections"
        - user: root
java:
    pkg.installed:
        - order: 2
        - names:
            - oracle-java8-installer
            - oracle-java8-set-default
        - require:
            - pkgrepo: java-ppa
            - file: java-home
            - cmd: accept-oracle-terms

{% else %}
openjdk-6-jre:
    pkg.installed:
        - order: 2
{% endif %}

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
