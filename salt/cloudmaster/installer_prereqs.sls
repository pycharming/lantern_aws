/home/lantern/repo:
    file.directory:
        - user: lantern
        - group: lantern
        - mode: 700

/home/lantern/secure:
    :

latest-repo:
    git.latest:
        - name: git://github.com/getlantern/lantern.git
        - rev: master
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

ui-submodule:
    cmd.run:
        - name: "git submodule update --init"
        - user: lantern
        - cwd: /home/lantern/repo
        - watch:
            - git: latest-repo

{% for platform in 'windows-x86','osx', 'linux-x86','linux-amd64' %}
{{ platform }}-repo:
    cmd.run:
        - name: "rm -rf {{ platform }}-repo ; cp -r repo {{ platform }}-repo"
        - user: lantern
        - group: lantern
        - cwd: /home/lantern
        - watch:
            - git: latest-repo
        - require:
            - cmd: ui-submodule
            - file: jres-dir
{% endfor %}

# The windows JRE is not really used, but install4j expects it there.  It
# would not even accept a dummy file with the same name.
{% for platform in 'windows-x86','linux-x86','linux-amd64' %}
{{ platform }}-jre-downloaded:
    cmd.run:
        - name: "wget -q https://d3g17h6tzzjzlu.cloudfront.net/{{ platform }}-jre.tar.gz"
        - unless: "test -f /home/lantern/{{ platform }}-jre.tar.gz"
        - user: lantern
        - group: lantern
        - cwd: "/home/lantern"

{{ platform }}-jre:
    cmd.run:
        - name: "cp /home/lantern/{{ platform }}-jre.tar.gz /home/lantern/{{ platform }}-repo/jres"
        - unless: "test -e /home/lantern/{{ platform }}-repo/jres/{{ platform }}-jre.tar.gz"
        - require:
            - cmd: {{ platform }}-jre-downloaded
            - cmd: {{ platform }}-repo
{% endfor %}

install4j:
    cmd.script:
        - source: salt://cloudmaster/install-install4j.bash
        - unless: "which install4jc"
        - user: root
        - group: root
        - cwd: /tmp
