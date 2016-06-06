include:
    - digitalocean
    - vultr
    - redis

/usr/bin/vps_sanity_checks.py:
  file.managed:
    - source: salt://vps_sanity_checks/vps_sanity_checks.py
    - user: root
    - group: root
    - mode: 755

"/usr/bin/vps_sanity_checks.py 2>&1 | logger -t vps_sanity_checks":
  cron.present:
    - user: lantern
    - hour: "*"
    - minute: "15,45"
    - identifier: vps_sanity_checks
    - require:
        - file: /usr/bin/vps_sanity_checks.py
        - pip: digitalocean
        - pip: vultr
        - pkg: python-redis
