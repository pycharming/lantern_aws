{% set jre_folder='/home/lantern/wrapper-repo/install/jres' %}
{% set access_data_file='/home/lantern/fallback.json' %}
{% set install_from=pillar.get('install-from', 'installer') %}
{% set proxy_protocol=pillar.get('proxy_protocol', 'tcp') %}
{% set auth_token=pillar.get('auth_token') %}
#XXX: hotfix; do a proper grain to fetch public IP.
{% if grains['ipv4'][0] == '127.0.0.1' %}
    {% set public_ip=(grains.get('public_ipv4') or grains['ipv4'][1]) %}
{% else %}
    {% set public_ip=(grains.get('public_ipv4') or grains['ipv4'][0]) %}
{% endif %}

# Keep install/common as the last one; it's being checked to make sure all
# folders have been initialized.
{% set dirs=['/home/lantern/wrapper-repo',
             '/home/lantern/wrapper-repo/lantern-ui',
             '/home/lantern/wrapper-repo/lantern-ui/app',
             '/home/lantern/wrapper-repo/lantern-ui/app/img',
             '/home/lantern/wrapper-repo/install',
             '/home/lantern/wrapper-repo/install/win',
             '/home/lantern/wrapper-repo/install/wrapper',
             jre_folder,
             '/home/lantern/wrapper-repo/install/common'] %}

# To filter through jinja.
{% set template_files=[
    ('/etc/ufw/applications.d/', 'lantern', 'ufw_rules', 'root', 644),
    ('/etc/init.d/', 'lantern', 'lantern.init', 'root', 700),
    ('/home/lantern/', 'build-wrappers.bash', 'build-wrappers.bash', 'lantern', 700),
    ('/home/lantern/', 'percent_mem.py', 'percent_mem.py', 'lantern', 700),
    ('/home/lantern/', 'upload_wrappers.py', 'upload_wrappers.py', 'lantern', 700),
    ('/home/lantern/', 'kill_lantern.py', 'kill_lantern.py', 'lantern', 700),
    ('/home/lantern/', 'report_stats.py', 'report_stats.py', 'lantern', 700),
    ('/home/lantern/', 'user_credentials.json', 'user_credentials.json', 'lantern', 400),
    ('/home/lantern/', 'client_secrets.json', 'client_secrets.json', 'lantern', 400),
    ('/home/lantern/', 'auth_token.txt', 'auth_token.txt', 'lantern', 400),
    ('/home/lantern/wrapper-repo/install/win/', 'lantern.nsi', 'lantern.nsi', 'lantern', 400),
    ('/home/lantern/secure/', 'env-vars.txt', 'env-vars.txt', 'lantern', 400),
    ('/home/lantern/wrapper-repo/', 'buildInstallerWrappers.bash', 'buildInstallerWrappers.bash', 'lantern', 500),
    ('/home/lantern/wrapper-repo/install/wrapper/', 'wrapper.install4j', 'wrapper.install4j', 'lantern', 500),
    ('/home/lantern/wrapper-repo/install/wrapper/', 'dpkg.bash', 'dpkg.bash', 'lantern', 500),
    ('/home/lantern/', 'fallback.json', 'fallback.json', 'lantern', 400),
    ('/home/lantern/', 'fte.props', 'fte.props', 'lantern', 400)] %}

# To send as is.
{% set literal_files=[
    ('/home/lantern/', 'installer_landing.html', 400),
    ('/home/lantern/secure/', 'bns_cert.p12', 400),
    ('/home/lantern/secure/', 'bns-osx-cert-developer-id-application.p12',
     400),
    ('/home/lantern/wrapper-repo/install/win/', 'osslsigncode', 700),
    ('/home/lantern/wrapper-repo/lantern-ui/app/img/', 'favicon.ico', 400),
    ('/home/lantern/wrapper-repo/install/common/', 'lantern.icns', 400),
    ('/home/lantern/wrapper-repo/install/common/', '128on.png', 400),
    ('/home/lantern/wrapper-repo/install/common/', '16off.png', 400),
    ('/home/lantern/wrapper-repo/install/common/', '16on.png', 400),
    ('/home/lantern/wrapper-repo/install/common/', '32off.png', 400),
    ('/home/lantern/wrapper-repo/install/common/', '32on.png', 400),
    ('/home/lantern/wrapper-repo/install/wrapper/', 'InstallDownloader.class', 400),
    ('/home/lantern/wrapper-repo/install/common/', '64on.png', 400)] %}

{% set jre_files=['windows-x86-jre.tar.gz',
                  'macosx-amd64-jre.tar.gz',
                  'linux-x86-jre.tar.gz',
                  'linux-amd64-jre.tar.gz'] %}

{% set lantern_pid='/var/run/lantern.pid' %}

include:
    - boto
    - install4j
    - lockfile

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

{% for dir,dst_filename,src_filename,user,mode in template_files %}
{{ dir+dst_filename }}:
    file.managed:
        - source: salt://fallback_proxy/{{ src_filename }}
        - template: jinja
        - context:
            lantern_pid: {{ lantern_pid }}
            install_from: {{ install_from }}
            proxy_protocol: {{ proxy_protocol }}
            auth_token: {{ auth_token }}
            public_ip: {{ public_ip }}
        - user: {{ user }}
        - group: {{ user }}
        - mode: {{ mode }}
        - require:
            - file: /home/lantern/wrapper-repo/install/common
            - pip: lockfile
{% endfor %}

{% for dir,filename,mode in literal_files %}
{{ dir+filename }}:
    file.managed:
        - source: salt://fallback_proxy/{{ filename }}
        - user: lantern
        - group: lantern
        - mode: {{ mode }}
        - require:
            - file: /home/lantern/wrapper-repo/install/common
{% endfor %}


{% for filename in jre_files %}

download-{{ filename }}:
    cmd.run:
        - name: 'wget -qct 3 https://s3.amazonaws.com/bundled-jres/{{ filename }}'
        - unless: 'test -e {{ jre_folder }}/{{ filename }}'
        - user: root
        - group: root
        - cwd: {{ jre_folder }}

{% endfor %}

install-lantern:
    cmd.script:
{% if install_from == 'git' %}
        - source: salt://fallback_proxy/install-lantern-from-git.bash
        - unless: "[ -e /home/lantern/lantern-repo/target ] && [ \"$(find /home/lantern/lantern-repo/target -maxdepth 1 -name 'lantern-*.jar')\" ]"
        - user: lantern
        - group: lantern
        - cwd: /home/lantern/
{% else %}
        - source: salt://fallback_proxy/install-lantern-from-installer.bash
        - unless: "which lantern"
        - user: root
        - group: root
        - cwd: /root
{% endif %}
        - template: jinja
        - stateful: yes

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
            {% for dir,dst_filename,src_filename,user,mode in template_files %}
            - file: {{ dir+dst_filename }}
            {% endfor %}
            {% for dir,filename,mode in literal_files %}
            - file: {{ dir+filename }}
            {% endfor %}

nsis:
    pkg.installed

open-proxy-port:
    cmd.run:
        - name: "ufw allow lantern_proxy"
        - require:
            - cmd: fallback-proxy-dirs-and-files

lantern-service:
    service.running:
        - name: lantern
        - enable: yes
        - require:
            - cmd: open-proxy-port
            - cmd: fallback-proxy-dirs-and-files
        - watch:
            # Restart when we get a new user to run as, or a new refresh token.
            - file: /home/lantern/user_credentials.json
            - cmd: install-lantern
            - file: /etc/init.d/lantern

report-completion:
    cmd.script:
        - source: salt://fallback_proxy/report_completion.py
        - template: jinja
        - context:
            public_ip: {{ public_ip }}
            access_data_file: {{ access_data_file }}
        - unless: "[ -e /home/lantern/reported_completion ]"
        - user: lantern
        - group: lantern
        - cwd: /home/lantern
        - require:
            - service: lantern-service
            # I need boto updated so I have the same version as the cloudmaster
            # and thus I can unpickle and delete the SQS message that
            # triggered the launching of this instance.
            - pip: boto==2.9.5
            - file: {{ access_data_file }}
            - cmd: generate-cert

zip:
    pkg.installed

nsis-inetc-plugin:
    cmd.run:
        - name: 'wget -qct 3 https://s3.amazonaws.com/lantern-aws/Inetc.zip && unzip -u Inetc.zip -d /usr/share/nsis/'
        - unless: 'test -e /tmp/Inetc.zip'
        - user: root
        - group: root
        - cwd: '/tmp'
        - require:
            - pkg: zip

python-dev:
    pkg.installed

build-essential:
    pkg.installed

psutil:
    pip.installed:
        - require:
            - pkg: build-essential
            - pkg: python-dev

librato-metrics:
    pip.installed

report-stats:
    cron.present:
        - name: /home/lantern/report_stats.py
        - minute: '*/10'
        - user: lantern
        - require:
            - file: /home/lantern/report_stats.py
            - pip: librato-metrics
            - pip: psutil
            - service: lantern

init-swap:
    cmd.script:
        - source: salt://fallback_proxy/make-swap.bash
        - unless: "[ $(swapon -s | wc -l) -gt 1 ]"
        - user: root
        - group: root


#{% if grains['controller'] == grains['production_controller'] %}
#check-lantern:
#    cron.present:
#        - name: /home/lantern/check_lantern.py
#        - user: root
#        - require:
#            - file: /home/lantern/check_lantern.py
#            - pip: psutil
#            - service: lantern
#{% endif %}

/etc/default/ufw:
    file.replace:
        - pattern: '^DEFAULT_FORWARD_POLICY="DROP"$'
        - repl:     'DEFAULT_FORWARD_POLICY="ACCEPT"'

/etc/ufw/sysctl.conf:
    file.append:
        - text: |
            net/ipv4/ip_forward=1
            net/ipv6/conf/default/forwarding=1

{% if proxy_protocol == 'tcp' %}
/etc/ufw/before.rules:
    file.append:
        - text: |
            *nat

            :PREROUTING ACCEPT - [0:0]
            # Redirect ports 80 and 443 to the Lantern proxy
            -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 62000
            -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 62443

            COMMIT

{% endif %}

restart-ufw:
    cmd.run:
        - name: 'service ufw restart'
        - user: root
        - group: root

# Dictionary of American English words for the dname generator in
# generate-cert.
wamerican:
    pkg.installed

generate-cert:
    cmd.script:
        - source: salt://fallback_proxy/gencert.py
        # Don't clobber the keystore of old fallbacks.
        - unless: '[ -e /home/lantern/littleproxy_keystore.jks ]'
        - require:
            - pkg: wamerican
