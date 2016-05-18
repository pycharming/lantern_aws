include:
  - redis

cfgsrv-env:
  file.append:
    - name: /etc/environment
    - text: |
        AUTH_TOKEN='{{ pillar['cfgsrv_token'] }}'
        {% if not pillar['in_production'] %}
          REDISCLOUD_URL='{{ pillar['cfgsrv_redis_url'] }}'
        {% else %}
          REDISCLOUD_URL='{{ pillar['cfgsrv_redis_url'].split('@')[0] }}@localhost:6379'
        {% endif %}
        PRODUCTION=true
        PORT=62000

stunnel4:
  pkg.installed

/etc/stunnel/stunnel.conf:
  file.managed:
    - source: salt://config_server/stunnel.conf
    - template: jinja
    - context:
        redis_host: {{ pillar['cfgsrv_redis_url'].split('@')[1] }}
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
    - require:
      - pkg: stunnel4

enable-stunnel:
  file.replace:
    - name: /etc/default/stunnel4
    - pattern: "ENABLED=0"
    - repl: "ENABLED=1"
    - append_if_not_found: yes
    - require:
      - pkg: stunnel4

restart-stunnel:
  cmd.run:
    - name: /etc/init.d/stunnel4 restart

/home/lantern/config-server.jar:
  file.managed:
    - source: salt://config_server/config-server.jar
    - mode: 755
    - owner: lantern

/etc/init/config-server.conf:
  file.managed:
    - source: salt://config_server/config-server.conf
    - mode: 644
    - template: jinja

config-server:
  service.running:
    - enable: yes
    - watch:
        - file: /home/lantern/config-server.jar
        - file: /etc/init/config-server.conf
        - cmd: restart-stunnel
