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

{% set libs=['redisq', 'do_util', 'vultr_util', 'vps_util', 'redis_util', 'misc_util'] %}

{% for lib in libs %}

/usr/local/lib/pylib/{{ lib }}.py:
    file.managed:
        - source: salt://cloudmaster/{{ lib }}.py
        - user: root
        - group: root
        - mode: 644

{% endfor %}


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