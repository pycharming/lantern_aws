include:
    - salt_cloud
    - lockfile
    - digitalocean
    - vultr
    - redis

/etc/ufw/applications.d/salt:
    file.managed:
        - source: salt://cloudmaster/ufw-rules
        - user: root
        - group: root
        - mode: 644

'ufw app update Salt ; ufw allow salt':
    cmd.run:
        - require:
            - file: /etc/ufw/applications.d/salt

/home/lantern/cloudmaster.py:
    file.managed:
        - source: salt://cloudmaster/cloudmaster.py
        - template: jinja
        - user: root
        - group: root
        - mode: 700
    cron.present:
        - user: root
        - minute: "*/1"
        - require:
            - pip: lockfile

/usr/bin/regenerate-fallbacks-list:
    file.managed:
        - source: salt://cloudmaster/regenerate_fallbacks_list.py
        - user: root
        - group: root
        - mode: 700

/usr/bin/accept-minions:
    file.managed:
        - source: salt://cloudmaster/accept_minions.py
        - user: root
        - group: root
        - mode: 700

sshpass:
  pkg.installed

{% set libs=['redisq', 'do_util', 'vultr_util', 'vps_util', 'redis_util', 'misc_util', 'mail_util'] %}

{% for lib in libs %}

/usr/local/lib/pylib/{{ lib }}.py:
    file.managed:
        - order: 1
        - source: salt://cloudmaster/{{ lib }}.py
        - template: jinja
        - user: root
        - group: root
        - mode: 644
        - makedirs: True

{% endfor %}

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
    - source: salt://cloudmaster/vps_sanity_checks.py
    - user: root
    - group: root
    - mode: 755

{% if pillar['in_production'] %}

"/usr/bin/vps_sanity_checks.py 2>&1 | logger -t vps_sanity_checks":
  cron.present:
    - user: lantern
    - minute: "30"
    - identifier: vps_sanity_checks
    - require:
        - file: /usr/bin/vps_sanity_checks.py
        - cron: REDIS_URL
        - cron: PYTHONPATH
        - cron: DO_TOKEN
        - cron: VULTR_APIKEY

{% endif %}

{% for svc in ['refill_srvq', 'retire', 'destroy'] %}

/usr/bin/{{ svc }}.py:
    file.managed:
        - source: salt://cloudmaster/{{ svc }}.py
        - user: root
        - group: root
        - mode: 755

{% for dc in ['doams3', 'vltok1'] %}

/etc/init/{{ svc }}_{{ dc }}.conf:
    file.managed:
        - source: salt://cloudmaster/{{ svc }}.conf
        - template: jinja
        - context:
            dc: {{ dc }}
        - user: root
        - group: root
        - mode: 600

{% if pillar['in_production'] %}
{{ svc }}_{{ dc }}:
    service.running:
        - enable: yes
        - require:
              - cmd: {{ svc }}-services-registered
{% endif %}

{% endfor %} {# dc #}

{% if pillar['in_production'] %}
{{ svc }}-services-registered:
    cmd.run:
        - name: 'initctl reload-configuration'
        - watch:
            - file: /usr/bin/{{ svc }}.py
            - file: /etc/init/{{ svc }}_doams3.conf
            - file: /etc/init/{{ svc }}_vltok1.conf
{% for lib in libs %}
            - file: /usr/local/lib/pylib/{{ lib }}.py
{% endfor %} {# lib #}
        - require:
            - pip: digitalocean
            - pip: vultr
            - pkg: python-redis
{% endif %}

{% endfor %} {# svc #}