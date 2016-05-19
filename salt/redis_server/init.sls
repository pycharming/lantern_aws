/etc/stunnel/stunnel_server.conf:
  file.managed:
    - source: salt://redis_server/stunnel_server.conf
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
    - require:
      - pkg: stunnel4

install-python-software-properties:
  cmd.run:
    - name: apt-get install -q python-software-properties

/etc/redis/redis_base.conf:
  file.managed:
    - order: 2
    - source: salt://redis_server/redis_base.conf
    - user: root
    - group: root
    - mode: 644
    - makedirs: True

/etc/redis/redis_auth.conf:
  file.managed:
    - order: 2
    - source: salt://redis_server/redis_auth.conf
    - user: root
    - group: root
    - mode: 644
    - makedirs: True

redis-includes:
    file.append:
      - name: /etc/redis/redis.conf
      - text: |
          include /etc/redis/redis_base.conf
          include /etc/redis/redis_auth.conf

{% if pillar.get('master', False) %}
/etc/redis/redis_master.conf:
  file.managed:
    - order: 2
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
    - order: 2
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

redis-server:
  pkgrepo.managed:
    - ppa: chris-lea/redis-server
    - require:
      - cmd: install-python-software-properties

  pkg.installed:
    - name: redis-server
    - refresh: True
    - version: 3:3.0.7-1chl1~trusty1

  service.running:
    - enable: yes
    - require:
        - pkg: stunnel4
    - watch:
        - file: /etc/redis/*

{% set rulefiles=['user.rules', 'user6.rules'] %}
{% for file in rulefiles %}
/lib/ufw/{{ file }}:
  file.managed:
    - order: 2
    - source: salt://redis_server/{{ file }}
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
{% endfor %}

ufw enable:
  cmd.run:
    - require:
      - pkg: ufw
      {% for file in rulefiles %}
      - file: /lib/ufw/{{ file }}
      {% endfor %}
