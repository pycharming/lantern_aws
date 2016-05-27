# In case we're switching back and forth between redis configurations, remove
# old REDIS_URL entries
redis-env:
  file.replace:
    - name: /etc/environment
    - append_if_not_found: True
    - pattern: "^REDIS_URL=.+$"
    - repl: "REDIS_URL={{ pillar['cfgsrv_redis_url'] }}"

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
