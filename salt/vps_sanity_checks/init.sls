include:
    - digitalocean
    - vultr
    - redis

REDIS_URL:
  cron.env_present:
    - user: lantern
    - value: {{ pillar['cfgsrv_redis_url'] }}

PYTHONPATH:
  cron.env_present:
    - user: lantern
    - value: /usr/local/lib/pylib

DO_TOKEN:
  cron.env_present:
    - user: lantern
    - value: {{ pillar['do_token'] }}

VULTR_APIKEY:
  cron.env_present:
    - user: lantern
    - value: {{ pillar['vultr_apikey'] }}

/usr/bin/vps_sanity_checks.py:
  file.managed:
    - source: salt://vps_sanity_checks/vps_sanity_checks.py
    - user: root
    - group: root
    - mode: 755

"/usr/bin/vps_sanity_checks.py 2>&1 | logger -t vps_sanity_checks":
  cron.present:
    - user: lantern
    - hour: "*/4"
    - minute: "30"
    - identifier: vps_sanity_checks
    - require:
        - file: /usr/bin/vps_sanity_checks.py
        - cron: REDIS_URL
        - cron: PYTHONPATH
        - cron: DO_TOKEN
        - cron: VULTR_APIKEY
        - pip: digitalocean
        - pip: vultr
        - pkg: python-redis