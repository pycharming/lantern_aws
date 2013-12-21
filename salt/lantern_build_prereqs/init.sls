{% if pillar.get('install-from') == 'git' %}
openjdk-6-jre:
    pkg.removed

java-prereqs:
    cmd.script:
        - source: salt://lantern_build_prereqs/install-java-prereqs.bash
        - unless: "[ -e /usr/lib/jvm/java-6-sun/bin/java ]"
        - user: root
        - cwd: /tmp
        - require:
            - pkg: openjdk-6-jre
    file.append:
        - name: /etc/profile
        - text: "export JAVA_HOME=/usr/lib/jvm/java-6-sun"

java:
    pkg.installed:
        - order: 2
        - names:
            - sun-java6-jre
            - sun-java6-bin
            - sun-java6-jdk
        - require:
            - cmd: java-prereqs
            - file: java-prereqs
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
