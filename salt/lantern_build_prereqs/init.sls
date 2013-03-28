java-prereqs:
    cmd.script:
        - source: salt://lantern_build_prereqs/install-java-prereqs.bash
        - unless: "which java"
        - user: root
        - cwd: /tmp
    file.append:
        - name: /etc/profile
        - text: "export JAVA_HOME=/usr/lib/jvm/java-6-sun"

java:
    pkg.installed:
        - names:
            - sun-java6-jre
            - sun-java6-bin
            - sun-java6-jdk
        - require:
            - cmd: java-prereqs
            - file: java-prereqs

maven:
    cmd.script:
        - source: salt://lantern_build_prereqs/install-maven.bash
        - unless: "which mvn"
        - user: root
        - cwd: /tmp
        - require:
            - pkg: java
