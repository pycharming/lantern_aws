/etc/stunnel/stunnel_server.conf:
  file.managed:
    - source: salt://redis_server/stunnel_server.conf
    - template: jinja
    - context:
        redis_host: {{ pillar['cfgsrv_redis_url'].split('@')[1] }}
        redis_domain: {{ pillar['cfgsrv_redis_url'].split('@')[1].split(":")[0] }}
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
    - require:
      - pkg: stunnel4

/etc/redis/redis_auth.conf:
  file.managed:
    - source: salt://redis_server/redis_auth.conf
    - user: root
    - group: root
    - mode: 644
    - makedirs: True

/etc/redis/redis.conf:
  file.managed:
    - source: salt://redis_server/redis.conf
    - user: root
    - group: root
    - mode: 644
    - makedirs: True

{% if pillar.get('is_redis_master', False) %}
/etc/redis/redis_master.conf:
  file.managed:
    - source: salt://redis_server/redis_master.conf
    - user: root
    - group: root
    - mode: 644
    - makedirs: True

/etc/redis/redis_slave.conf:
  file.absent

include-master:
    file.append:
      - name: /etc/redis/redis.conf
      - text: include /etc/redis/redis_master.conf

exclude-slave:
    file.replace:
      - name: /etc/redis/redis.conf
      - pattern: include /etc/redis/redis_slave.conf
      - repl:

{% else %}

/etc/redis/redis_slave.conf:
  file.managed:
    - source: salt://redis_server/redis_slave.conf
    - user: root
    - group: root
    - mode: 644
    - makedirs: True

/etc/redis/redis_master.conf:
  file.absent

include-slave:
    file.append:
      - name: /etc/redis/redis.conf
      - text: include /etc/redis/redis_slave.conf

exclude-master:
    file.replace:
      - name: /etc/redis/redis.conf
      - pattern: include /etc/redis/redis_master.conf
      - repl:
{% endif %}

redis-ulimit:
    file.append:
      - name: /etc/security/limits.conf
      - text: |
          redis            soft    nofile            128000
          redis            hard    nofile            128000

redis-server:
  pkgrepo.managed:
    - ppa: chris-lea/redis-server

  pkg.installed:
    - name: redis-server
    - refresh: True
    - version: 3:3.0.7-1chl1~trusty1
      - pkgrepo: redis-server

disable-redis-server-sysv:
  cmd.run:
    - name: /etc/init.d/redis-server stop ; update-rc.d redis-server disable ; update-rc.d redis-server remove ; rm /etc/init.d/redis-server ; echo "done"
    - require:
      - pkg: redis-server

/etc/init/redis-server.conf:
  file.managed:
    - source: salt://redis_server/redis-server.conf
    - user: root
    - group: root
    - mode: 644

redis-server-running:
  service.running:
    - name: redis-server
    - enable: yes
    - require:
        - pkg: stunnel4
        - pkg: redis-server
        - cmd: disable-redis-server-sysv
    - watch:
        - file: /etc/redis/*
        - file: /etc/init/redis-server.conf
        - cmd: stunnel4-deps

{% set rulefiles=['user.rules', 'user6.rules'] %}
{% for file in rulefiles %}
/lib/ufw/{{ file }}:
  file.managed:
    - source: salt://redis_server/{{ file }}
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
{% endfor %}

ufw reload:
  cmd.run:
    - require:
      - pkg: ufw
    - watch:
      {% for file in rulefiles %}
      - file: /lib/ufw/{{ file }}
      {% endfor %}
