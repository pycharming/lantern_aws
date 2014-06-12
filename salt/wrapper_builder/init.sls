{% set jre_folder='/home/lantern/wrapper-repo/install/jres' %}
{% set wrapper_builder_pid='/var/run/wrapper_builder.pid' %}
{% from 'ip.sls' import external_ip %}
#XXX: hotfix; do a proper grain to fetch public IP.

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
    ('/etc/init.d/', 'wrapper_builder', 'wrapper_builder.init', 'root', 700),
    ('/home/lantern/', 'wrapper_builder.py', 'wrapper_builder.py', 'lantern', 700),
    ('/home/lantern/', 'check_wrapper_builder.py', 'check_wrapper_builder.py', 'root', 700)] %}

# To send as is
{% set literal_files=[
    ('/home/lantern/', 'build-wrappers.bash', 700),
    ('/home/lantern/wrapper-repo/install/win/', 'lantern.nsi', 400),
    ('/home/lantern/secure/', 'env-vars.txt', 400),
    ('/home/lantern/wrapper-repo/', 'buildInstallerWrappers.bash', 500),
    ('/home/lantern/wrapper-repo/install/wrapper/', 'wrapper.install4j', 500),
    ('/home/lantern/wrapper-repo/install/wrapper/', 'dpkg.bash', 500),
    ('/home/lantern/', 'installer_landing.html', 400),
    ('/home/lantern/secure/', 'bns_cert.p12', 400),
    ('/home/lantern/secure/', 'bns-osx-cert-developer-id-application.p12', 400),
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

include:
    - boto
    - install4j

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
        - source: salt://wrapper_builder/{{ src_filename }}
        - template: jinja
        - user: {{ user }}
        - group: {{ user }}
        - mode: {{ mode }}
        - context:
            wrapper_builder_pid: {{ wrapper_builder_pid }}
            external_ip: {{ external_ip(grains) }}
        - require:
            - file: /home/lantern/wrapper-repo/install/common
{% endfor %}

{% for dir,filename,mode in literal_files %}
{{ dir+filename }}:
    file.managed:
        - source: salt://wrapper_builder/{{ filename }}
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

# Join point that waits for prerequisites and presents a single prerequisite to
# downstream states.
all-dirs-and-files:
    cmd.run:
        - name: ":"
        - require:
            - file: /home/lantern/secure
            {% for dir in dirs %}
            - file: {{ dir }}
            {% endfor %}
            {% for dir,dst_filename,src_filename,user,mode in template_files %}
            - file: {{ dir+dst_filename }}
            {% endfor %}
            {% for dir,filename,mode in literal_files %}
            - file: {{ dir+filename }}
            {% endfor %}
            {% for filename in jre_files %}
            - cmd: download-{{ filename }}
            {% endfor %}

nsis:
    pkg.installed

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
        - name: psutil==2.1.0
        - require:
            - pkg: build-essential
            - pkg: python-dev

wrapper_builder:
    service.running:
        - enable: yes
        - require:
            - cmd: all-dirs-and-files
            - cmd: nsis-inetc-plugin
        - watch:
            - file: /home/lantern/wrapper_builder.py
            - file: /etc/init.d/wrapper_builder


{% if grains['controller'] == grains.get('production_controller', 'lanternctrl1-2') %}
check-wrapper-builder:
    cron.present:
        - name: /home/lantern/check_wrapper_builder.py
        - user: root
        - minute: '*/1'
        - require:
            - file: /home/lantern/check_wrapper_builder.py
            - pip: psutil
            - service: wrapper_builder
{% endif %}
