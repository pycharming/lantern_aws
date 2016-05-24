redis-env:
  file.append:
    - name: /etc/environment
    - text: "REDIS_URL={{ pillar['cfgsrv_redis_url'] }}"

# In case we're switching back and forth between redis configurations, replace
# what may have already been in /etc/environment.
replace-redis-env:
  file.replace:
    - name: /etc/environment
    - pattern: "REDIS_URL=.+"
    - repl: "REDIS_URL={{ pillar['cfgsrv_redis_url'] }}"
    - require:
      - file: redis-env

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
