pylib-pythonpath:
  file.append:
    - order: 2
    - name: /etc/environment
    - text: "PYTHONPATH=/usr/local/lib/pylib"

{% set libs=['redisq', 'do_util', 'vultr_util', 'vps_util', 'redis_util', 'misc_util', 'alert'] %}

{% for lib in libs %}

/usr/local/lib/pylib/{{ lib }}.py:
  file.managed:
    - order: 2
    - source: salt://pylib/{{ lib }}.py
    - template: jinja
    - user: root
    - group: root
    - mode: 644
    - makedirs: True

{% endfor %}
