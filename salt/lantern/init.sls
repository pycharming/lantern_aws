
install-lantern:
    cmd.script:
        - source: salt://fallback_proxy/install-lantern-from-git.bash
        - unless: "[ -e /home/lantern/lantern-repo/target ] && [ \"$(find /home/lantern/lantern-repo/target -maxdepth 1 -name 'lantern-*.jar')\" ]"
        - user: lantern
        - group: lantern
        - cwd: /home/lantern/
        - template: jinja
        - stateful: yes
