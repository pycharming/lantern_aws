include:
    - digitalocean
    - linode
    - vultr
    - redis

# Quick hack to get this into cloudmasters without adding it to lantern_aws.
# config-server is in a private repo.
update-config-server-uberjar:
  cmd.run:
    - name: "cp -f /home/lantern/config-server.jar /srv/salt/config_server/config-server.jar"
    - unless: "[ ! -e /home/lantern/config-server.jar ]"

/etc/ufw/applications.d/salt:
    file.managed:
        - source: salt://cloudmaster/ufw-rules-salt
        - user: root
        - group: root
        - mode: 644

'ufw app update Salt ; ufw allow salt':
    cmd.run:
        - watch:
            - file: /etc/ufw/applications.d/salt

{# Old name for refill_region_srvq. #}

refill_srvq:
  service.dead:
    - enable: no

/etc/init/refill_srvq.conf:
  file.absent:
    - require:
       - service: refill_srvq

{% for executable in ['refill_srvq', 'offload', 'retire', 'destroy', 'check_redis'] %}
/usr/bin/{{ executable }}.py:
    file.managed:
        - source: salt://cloudmaster/{{ executable }}.py
        - user: root
        - group: root
        - mode: 755
{% endfor %}

{% for svc, executable in [('refill_cm_srvq', 'refill_srvq'),
                           ('refill_region_srvq', 'refill_srvq'),
                           ('offload', 'offload'),
                           ('retire', 'retire'),
                           ('destroy', 'destroy')] %}

{# Only launch regional servers from select datacenters. #}

{% if svc != 'refill_region_srvq'
       or pillar['cloudmaster_name'] in ['cm-donyc3', 'cm-vltok1', 'cm-dosgp1', 'cm-dosfo1', 'cm-doams3',
                                         'cm-donyc3staging', 'cm-dosgp1staging', 'cm-doams3staging'] %}

/etc/init/{{ svc }}.conf:
    file.managed:
        - source: salt://cloudmaster/{{ svc }}.conf
        - template: jinja
        - user: root
        - group: root
        - mode: 600

{{ svc }}:
    service.running:
        - enable: yes
        - require:
              - cmd: {{ svc }}-services-registered


{{ svc }}-services-registered:
    cmd.run:
        - name: 'initctl reload-configuration'
        - watch:
            - file: /usr/bin/{{ executable }}.py
            - file: /etc/init/{{ svc }}.conf
        - require:
            - pip: digitalocean
            - pip: vultr
            - pkg: python-redis

{% else %}

{{ svc }}:
  service.dead:
    - enable: no

/etc/init/{{ svc }}.conf:
  file.absent:
    - require:
        - service: {{ svc }}

{% endif %}

{% endfor %} {# svc #}

{# Redis DB hosted in Cloudmaster only for testing purposes #}
{% if not pillar['in_production'] %}

/etc/ufw/applications.d/redis-testing:
    file.managed:
        - source: salt://cloudmaster/ufw-rules-redis-testing
        - user: root
        - group: root
        - mode: 644

'ufw app update Redis ; ufw allow redis':
    cmd.run:
        - require:
            - file: /etc/ufw/applications.d/redis-testing
            - pkg: redis-server

redis-server:
    pkg.installed:
        - name: redis-server
    service.running:
        - enable: True
        - require:
            - pkg: redis-server
            - file: /var/log/redis
        - watch:
            - file: /etc/redis/redis.conf

/var/log/redis:
    file.directory:
        - user: redis
        - group: adm
        - mode: 2750

/etc/redis/redis.conf:
    file.managed:
        - source: salt://cloudmaster/redis-testing.conf.jinja
        - template: jinja
        - defaults:
          bind: 0.0.0.0
          port: 6379
          maxmemory: 0
          loglevel: notice
          databases: 1
        - require:
            - pkg: redis-server

{% endif %}

# Utilities for deploying salt updates.

/usr/bin/check_deployment.py:
  file.managed:
    - source: salt://cloudmaster/check_deployment.py
    - mode: 755

/usr/bin/kill_running_highstates.py:
  file.managed:
    - source: salt://cloudmaster/kill_running_highstates.py
    - mode: 755

# Utility to launch config servers (XXX: generalize).
/usr/bin/launch_config_server.py:
  file.managed:
    - source: salt://cloudmaster/launch_config_server.py
    - mode: 755

# This transitional module has been phased out, but apparently Salt still picks
# it up as the Digital Ocean driver if present from an old installation.
#
# This suggests making sure to nuke the old installation altogether when
# upgrading Salt, but as of this writing this problem had crept into many
# cloudmasters.
delete-obsolete-digital-ocean-v2-driver:
  file.absent:
    - names:
        - /usr/lib/python2.7/dist-packages/salt/cloud/clouds/digital_ocean_v2.py
        - /usr/lib/python2.7/dist-packages/salt/cloud/clouds/digital_ocean_v2.pyc

# Check redis periodically
/usr/bin/check_redis.py 2>&1 | logger -t check_redis:
  cron.present:
    - identifier: check_redis
    - minute: "*"
    - user: lantern
    - require:
        - file: /usr/bin/check_redis.py
