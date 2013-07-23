#XXX: some of these config files are actually specific to the use that
#cloudmaster makes of salt-cloud.  Move there.
/etc/salt/lantern.pem:
    file.managed:
        - source: salt://salt_cloud/{{ grains['aws_region'] }}.pem
        - user: root
        - group: root
        - mode: 600

/etc/salt/cloudmaster.id_rsa:
    file.managed:
        - source: salt://salt_cloud/cloudmaster.id_rsa
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

apache-libcloud:
    pip.installed:
        - upgrade: yes

salt-cloud==0.8.9:
    pip.installed:
        - require:
              - pip: apache-libcloud

bootstrap-script:
    file.managed:
        - name: /usr/local/lib/python2.7/dist-packages/saltcloud/deploy/bootstrap-salt.sh
        - source: salt://salt_cloud/bootstrap.bash
        # This is how the pip installation of salt-cloud has them.
        - mode: 644
        - user: root
        - group: staff
        - require:
            # To make sure we override the default version.
            - pip: salt-cloud==0.8.9
