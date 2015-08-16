include:
  - vultr
  - digitalocean
  - redis

/home/lantern/check_vpss.py:
  file.managed:
    - source: salt://check_vpss/check_vpss.py
    - template: jinja
    - user: lantern
    - group: lantern
    - mode: 755

{% if pillar['in_production'] %}
/home/lantern/check_vpss.py 2>&1 | /usr/bin/logger -t check_vpss:
  cron.present:
    - hour: 2
    - minute: 1
    - user: lantern
    - require:
        - pip: digitalocean
        - pip: vultr
        - pkg: python-redis
        - file: /home/lantern/check_vpss.py
{% endif %}