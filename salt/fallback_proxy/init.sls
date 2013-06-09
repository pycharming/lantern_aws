{% set iwbfiles=[
    ('/home/lantern/secure/', 'env-vars.txt', 400),
    ('/home/lantern/secure/', 'bns_cert.p12', 400),
    ('/home/lantern/secure/', 'bns-osx-cert-developer-id-application.p12', 400),
    ('/home/lantern/repo/', 'buildInstallerWrappers.bash', 500),
    ('/home/lantern/repo/install/', 'wrapper.install4j', 500),
    ('/home/lantern/repo/install/common/', 'lantern.icns', 400),
    ('/home/lantern/repo/install/common/', '128on.png', 400),
    ('/home/lantern/repo/install/common/', '16off.png', 400),
    ('/home/lantern/repo/install/common/', '16on.png', 400),
    ('/home/lantern/repo/install/common/', '32off.png', 400),
    ('/home/lantern/repo/install/common/', '32on.png', 400),
    ('/home/lantern/repo/install/common/', '64on.png', 400)] %}

include:
    - install4j

openjdk-6-jre:
    pkg.installed

/home/lantern/secure:
    file.directory:
        - user: lantern
        - group: lantern
        - dir_mode: 500
        - file_mode: 400
        - recurse:
            - user
            - group
            - mode

/home/lantern/repo/install/common:
    file.directory:
        - makedirs: True

/home/lantern/repo:
    file.directory:
        - user: lantern
        - group: lantern
        - dir_mode: 750
        - recurse:
            - user
            - group
            - mode
        - require:
            - file: /home/lantern/repo/install/common

{% for dir,filename,mode in iwbfiles %}
{{ dir+filename }}:
    file.managed:
        - source: salt://fallback_proxy/{{ filename }}
        - user: lantern
        - group: lantern
        - mode: {{ mode }}
        - require:
            - file: /home/lantern/repo/install/common
{% endfor %}

build-wrappers:
    cmd.run:
        - name: "source ../secure/env-vars.txt && /home/lantern/repo/buildInstallerWrappers.bash 0.21.3-11"
        - user: lantern
        - cwd: /home/lantern/repo
        - unless: "[ -e /home/lantern/repo/install/*.exe ]"
        - require:
            - cmd: install4j
            - pkg: openjdk-6-jre
            {% for dir,filename,mode in iwbfiles %}
            - file: {{ dir+filename }}
            {% endfor %}
