{% set dirs=['/home/lantern/repo',
             '/home/lantern/repo/install',
             '/home/lantern/repo/install/common'] %}

{% set txtfiles=[
    ('/home/lantern/', 'getlanternversion.py', 700),
    ('/home/lantern/', 'report_completion.py', 700),
    ('/home/lantern/', 'user_credentials.json', 400),
    ('/home/lantern/', 'client_secrets.json', 400),
    ('/home/lantern/secure/', 'env-vars.txt', 400),
    ('/home/lantern/repo/', 'buildInstallerWrappers.bash', 500),
    ('/home/lantern/repo/install/wrapper/', 'wrapper.install4j', 500),
    ('/home/lantern/repo/install/wrapper/', 'dpkg.bash', 500),
    ('/home/lantern/repo/install/wrapper/', 'fallback.json', 400)] %}

# The only difference is jinja doesn't like these.
{% set binaries=[
    ('/home/lantern/', 'littleproxy_keystore.jks', 400),
    ('/home/lantern/secure/', 'bns_cert.p12', 400),
    ('/home/lantern/secure/', 'bns-osx-cert-developer-id-application.p12',
     400),
    ('/home/lantern/repo/install/common/', 'lantern.icns', 400),
    ('/home/lantern/repo/install/common/', '128on.png', 400),
    ('/home/lantern/repo/install/common/', '16off.png', 400),
    ('/home/lantern/repo/install/common/', '16on.png', 400),
    ('/home/lantern/repo/install/common/', '32off.png', 400),
    ('/home/lantern/repo/install/common/', '32on.png', 400),
    ('/home/lantern/repo/install/wrapper/', 'InstallDownloader.class', 400),
    ('/home/lantern/repo/install/common/', '64on.png', 400)] %}

include:
    - install4j
    - boto

openjdk-6-jre:
    pkg.installed

/home/lantern/secure:
    file.directory:
        - user: lantern
        - group: lantern
        - mode: 500

{% for dir in dirs %}
{{ dir }}:
    file.directory:
        - user: lantern
        - group: lantern
        - dir_mode: 700
        - makedirs: yes
{% endfor %}

{% for dir,filename,mode in txtfiles %}
{{ dir+filename }}:
    file.managed:
        - source: salt://fallback_proxy/{{ filename }}
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: {{ mode }}
        - require:
            - file: /home/lantern/repo/install/common
{% endfor %}

{% for dir,filename,mode in binaries %}
{{ dir+filename }}:
    file.managed:
        - source: salt://fallback_proxy/{{ filename }}
        - user: lantern
        - group: lantern
        - mode: {{ mode }}
        - require:
            - file: /home/lantern/repo/install/common
{% endfor %}

install-lantern:
    cmd.script:
        - source: salt://fallback_proxy/install-lantern.bash
        - unless: "which lantern"
        - user: root
        - group: root
        - cwd: /root

fallback-proxy-dirs-and-files:
    cmd.run:
        - name: ":"
        - require:
            - file: /home/lantern/secure
            - file: /etc/init.d/lantern
            - file: /etc/ufw/applications.d/lantern
            {% for dir in dirs %}
            - file: {{ dir }}
            {% endfor %}
            {% for dir,filename,mode in txtfiles %}
            - file: {{ dir+filename }}
            {% endfor %}
            {% for dir,filename,mode in binaries %}
            - file: {{ dir+filename }}
            {% endfor %}

build-wrappers:
    cmd.script:
        - source: salt://fallback_proxy/build-wrappers.bash
        - user: lantern
        - cwd: /home/lantern/repo
        - unless: "[ -e /home/lantern/wrappers_built ]"
        - require:
            - cmd: fallback-proxy-dirs-and-files
            - cmd: install4j
            - pkg: openjdk-6-jre
            # We need lantern in order to know which version to install.
            - cmd: install-lantern

/etc/init.d/lantern:
    file.managed:
        - source: salt://fallback_proxy/lantern.init
        - template: jinja
        - user: root
        - group: root
        - mode: 700

/etc/ufw/applications.d/lantern:
    file.managed:
        - source: salt://fallback_proxy/ufw_rules
        - template: jinja
        - user: root
        - group: root
        - mode: 644

open-proxy-port:
    cmd.run:
        - name: "ufw allow lantern_proxy"
        - require:
            - cmd: fallback-proxy-dirs-and-files

upload-wrappers:
    cmd.script:
        - source: salt://fallback_proxy/upload_wrappers.py
        - template: jinja
        - unless: "[ -e /home/lantern/uploaded_wrappers ]"
        - user: lantern
        - group: lantern
        - cwd: /home/lantern/repo/install
        - require:
            - cmd: build-wrappers

lantern-service:
    service.running:
        - name: lantern
        - enable: yes
        - require:
            - cmd: open-proxy-port
            - cmd: upload-wrappers
            - cmd: fallback-proxy-dirs-and-files
        - watch:
            # Restart when we get a new user to run as, or a new refresh token.
            - file: /home/lantern/user_credentials.json

report-completion:
    cmd.script:
        - source: salt://fallback_proxy/report_completion.py
        - template: jinja
        - unless: "[ -e /home/lantern/reported_completion ]"
        - user: lantern
        - group: lantern
        - cwd: /home/lantern
        - require:
            - service: lantern-service
            - cmd: upload-wrappers
            # I need boto updated so I have the same version as the cloudmaster
            # and thus I can unpickle and delete the SQS message that
            # triggered the launching of this instance.
            - pip: boto==2.9.5
