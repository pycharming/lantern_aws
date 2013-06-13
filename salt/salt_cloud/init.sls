#XXX: these config files are actually specific to the use that
#cloudmaster makes of salt-cloud.  Move there.
/etc/salt/lantern.pem:
    file.managed:
        - source: salt://salt_cloud/{{ grains['aws_region'] }}.pem
        - user: root
        - group: root
        - mode: 600

/etc/salt/cloud:
    file.managed:
        - source: salt://salt_cloud/cloud
        - template: jinja
        - user: root
        - group: root
        - mode: 600

/etc/salt/cloud.profiles:
    file.managed:
        - source: salt://salt_cloud/cloud.profiles
        - template: jinja
        - user: root
        - group: root
        - mode: 600

python-libcloud:
    pkg.installed

salt-cloud:
    pip.removed: []
    git.latest:
        - name: git://github.com/saltstack/salt-cloud.git
        - rev: 22f249e46ac115d957d90673bd47e759cd1a83fc
        - target: /root/salt-cloud-repo
    cmd.run:
        - name: "python setup.py install"
        - cwd: /root/salt-cloud-repo
        - user: root
        - group: root
        - require:
            - git: salt-cloud
            - pkg: python-libcloud

# This version is broken.  Using git until we get a pip release that works.
#salt-cloud==0.8.8:
#    pip.installed:
#        - require:
#              - pkg: python-libcloud
