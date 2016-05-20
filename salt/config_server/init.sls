include:
  - redis

cfgsrv-env:
  file.append:
    - name: /etc/environment
    - text: |
        AUTH_TOKEN='{{ pillar['cfgsrv_token'] }}'
        REDISCLOUD_URL='{{ pillar['cfgsrv_redis_url'] }}'
        PRODUCTION=true
        PORT=62000

/etc/stunnel/stunnel_client.conf:
  file.managed:
    - source: salt://config_server/stunnel_client.conf
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
    - require:
      - pkg: stunnel4

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
    - order: last
    - enable: yes
    - require:
        - service: stunnel4
    - watch:
        - file: /home/lantern/config-server.jar
        - file: /etc/init/config-server.conf
        - cmd: stunnel4-deps
