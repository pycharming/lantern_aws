/home/lantern/repo:
    file.directory:
        - user: lantern
        - group: lantern
        - mode: 700

latest-repo:
    git.latest:
        - name: git://github.com/getlantern/lantern.git
        - rev: latest
        - submodules: yes
        - target: /home/lantern/repo
        - runas: lantern
        - require:
            - file: /home/lantern/repo

jres-dir:
    file.directory:
        - name: /home/lantern/repo/install/jres
        - user: lantern
        - group: lantern
        - mode: 700
        - require:
            - git: latest-repo

# The windows JRE is not really used, but install4j expects it there.  It
# would not even accept a dummy file with the same name.
{% for platform in 'windows-x86','linux-x86','linux-amd64' %}
{{ platform }}-jre-downloaded:
    cmd.run:
        - name: "wget -q https://d3g17h6tzzjzlu.cloudfront.net/{{ platform }}-jre.tar.gz"
        - unless: "test -f /home/lantern/repo/install/jres/{{ platform }}-jre.tar.gz"
        - user: lantern
        - group: lantern
        - cwd: "/home/lantern/repo/install/jres"
        - require:
            - git: latest-repo
            - file: jres-dir
{% endfor %}

install4j:
    cmd.script:
        - source: salt://cloudmaster/install-install4j.bash
        - unless: "which install4jc"
        - user: root
        - group: root
        - cwd: /tmp
