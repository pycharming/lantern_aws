redis-env:
  file.append:
    - name: /etc/environment
    - text: "REDIS_URL={{ pillar['cfgsrv_redis_url'] }}"

python-hiredis:
  pkg.installed

python-redis:
  pkg.installed:
    - require:
        - pkg: python-hiredis