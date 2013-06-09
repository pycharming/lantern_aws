{% set iwbfiles=[
    ('/home/lantern/secure/', 'env-vars.txt', 400),
    ('/home/lantern/secure/', 'bns_cert.p12', 400),
    ('/home/lantern/secure/', 'bns-osx-cert-developer-id-application.p12', 400),
    ('/home/lantern/repo/', 'buildInstallerWrappers.bash', 500),
    ('/home/lantern/repo/install/wrapper/', 'wrapper.install4j', 500),
    ('/home/lantern/repo/install/wrapper/', 'dpkg.bash', 500),
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
        #XXX: version!
        - name: "source ../secure/env-vars.txt && /home/lantern/repo/buildInstallerWrappers.bash $(../getlanternversion.py)"
        - user: lantern
        - cwd: /home/lantern/repo
        - unless: "[ -e /home/lantern/repo/install/*.exe ]"
        - require:
            - cmd: install4j
            - pkg: openjdk-6-jre
            {% for dir,filename,mode in iwbfiles %}
            - file: {{ dir+filename }}
            {% endfor %}
            - file: /home/lantern/getlanternversion.py
            - cmd: install-lantern

install-lantern:
    cmd.script:
        - source: salt://fallback_proxy/install-lantern.bash
        - unless: "which lantern"
        - user: root
        - group: root
        - cwd: /root

/etc/init.d/lantern:
    file.managed:
        - source: salt://fallback_proxy/lantern.init
        - template: jinja
        - user: root
        - group: root
        - mode: 700

/home/lantern/user_credentials.json:
    file.managed:
        - source: salt://fallback_proxy/user_credentials.json
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: 400

/home/lantern/client_secrets.json:
    file.managed:
        - source: salt://fallback_proxy/user_credentials.json
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: 400

/home/lantern/littleproxy_keystore.jks:
    file.managed:
        - source: salt://fallback_proxy/littleproxy_keystore.jks
        - user: lantern
        - group: lantern
        - mode: 400

/etc/ufw/applications.d/lantern:
    file.managed:
        - source: salt://fallback_proxy/ufw_rules
        - user: root
        - group: root
        - mode: 644

/home/lantern/getlanternversion.py:
    file.managed:
        - source: salt://home/lantern/getlanternversion.py
        - user: lantern
        - group: lantern
        - mode: 700

open-proxy-port:
    cmd.run:
        - name: "ufw allow lantern_proxy"
        - require:
            - file: /etc/ufw/applications.d/lantern

upload-wrappers:
    cmd.script:
        - source: salt://lantern_aws/upload_wrappers.py
        - user: lantern
        - group: lantern
        - cwd: /home/lantern/repo/install
        - require:
            - cmd: build-wrappers
lantern:
    service.running:
        - enable: yes
        - require:
            - file: /etc/init.d/lantern
            - file: /home/lantern/user_credentials.json
            - file: /home/lantern/
            - cmd: open-proxy-port
            - cmd: upload-wrappers

# upload-wrappers


