# In case we're switching back and forth between redis configurations, remove
# old REDIS_URL entries
clean-redis-env:
  file.line:
    - name: /etc/environment
    - content: ""
    - match: "REDIS_URL=(?!{{ pillar['cfgsrv_redis_url'] }}$)"
    - mode: Delete

redis-env:
  file.append:
    - name: /etc/environment
    - text: "REDIS_URL={{ pillar['cfgsrv_redis_url'] }}"
    - require:
      - file: clean-redis-env

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
