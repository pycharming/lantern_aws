include:
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
        - watch:
            - file: /etc/ufw/applications.d/salt

/usr/bin/regenerate-fallbacks-list:
    file.managed:
        - source: salt://cloudmaster/regenerate_fallbacks_list.py
        - user: root
        - group: root
        - mode: 700

sshpass:
  pkg.installed

{% set libs=['redisq', 'do_util', 'vultr_util', 'vps_util', 'redis_util', 'misc_util', 'mail_util'] %}

{% for lib in libs %}

/usr/local/lib/pylib/{{ lib }}.py:
    file.managed:
        - order: 2
        - source: salt://cloudmaster/{{ lib }}.py
        - template: jinja
        - user: root
        - group: root
        - mode: 644
        - makedirs: True

{% endfor %}


{% for svc in ['refill_srvq', 'retire', 'destroy'] %}

/usr/bin/{{ svc }}.py:
    file.managed:
        - source: salt://cloudmaster/{{ svc }}.py
        - user: root
        - group: root
        - mode: 755

{% if pillar['in_production'] %}


/etc/init/{{ svc }}.conf:
    file.managed:
        - source: salt://cloudmaster/{{ svc }}.conf
        - template: jinja
        - user: root
        - group: root
        - mode: 600

{{ svc }}:
    service.running:
        - enable: yes
        - require:
              - cmd: {{ svc }}-services-registered


{{ svc }}-services-registered:
    cmd.run:
        - name: 'initctl reload-configuration'
        - watch:
            - file: /usr/bin/{{ svc }}.py
            - file: /etc/init/{{ svc }}.conf
{% for lib in libs %}
            - file: /usr/local/lib/pylib/{{ lib }}.py
{% endfor %} {# lib #}
        - require:
            - pip: digitalocean
            - pip: vultr
            - pkg: python-redis
{% endif %}

{% endfor %} {# svc #}