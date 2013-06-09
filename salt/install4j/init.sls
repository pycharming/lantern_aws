install4j:
    cmd.script:
        - source: salt://install4j/install-install4j.bash
        - unless: "which install4jc"
        - user: root
        - group: root
        - cwd: /tmp
