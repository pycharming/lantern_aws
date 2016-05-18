redis-env:
  file.append:
    - name: /etc/environment
    - text: "REDIS_URL={{ pillar['cfgsrv_redis_url'] }}"

python-hiredis:
  pkg.removed

python-redis:
  pkg.removed

hiredis:
  pip.installed:
    - upgrade: yes

redis:
  pip.installed:
    - upgrade: yes
    - require:
        - pip: hiredis
