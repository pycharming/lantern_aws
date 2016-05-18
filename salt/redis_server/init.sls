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

redis-server:
  pkgrepo.managed:
    - ppa: rwky/redis
    - require:
      - cmd: install-python-software-properties

  pkg.installed:
    - name: redis-server
    - refresh: True

{% set rulefiles=['user.rules', 'user6.rules'] %}
{% for file in rulefiles %}
/lib/ufw/{{ file }}:
  file.managed:
    - order: 2
    - source: salt://redis_server/{{ file }}
    - template: jinja
    - user: root
    - group: root
    - mode: 640
    - makedirs: True
{% endfor %}

ufw enable:
  cmd.run:
    - require:
      - pkg: ufw
      {% for file in rulefiles %}
      - file: /lib/ufw/{{ file }}
      {% endfor %}
