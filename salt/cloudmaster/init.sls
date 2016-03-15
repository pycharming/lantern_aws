include:
    - digitalocean
    - vultr
    - redis

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

sshpass:
  pkg.installed

{% for svc in ['refill_srvq', 'retire', 'destroy'] %}

/usr/bin/{{ svc }}.py:
    file.managed:
        - source: salt://cloudmaster/{{ svc }}.py
        - user: root
        - group: root
        - mode: 755

{# Only launch servers from Amsterdam and Singapore. #}

{% if pillar['in_production']
      and (svc != 'refill_srvq'
           or pillar['cloudmaster_name'] in ['cm-donyc3', 'cm-dosgp1', 'cm-vlpar1']) %}

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
            - file: /usr/bin/{{ svc }}.py
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
