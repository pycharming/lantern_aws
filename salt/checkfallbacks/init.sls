{% from 'install_from_release.sls' import install_from_release %}

{# define cmd: checkfallbacks-installed #}
{{ install_from_release('checkfallbacks', '0.0.20') }}

redis:
  pkg.installed

hiredis:
  pkg.installed

/usr/bin/checkfallbacks.py:
  file.managed:
    - source: salt://checkfallbacks/checkfallbacks.py
    - user: root
    - group: root
    - mode: 755

"/usr/bin/checkfallbacks.py | logger -t checkfallbacks":
{% if pillar['in_production'] %}
  cron.present:
    - minute: '*/11'
    - user: lantern
    - require:
        - pkg: redis
        - cmd: checkfallbacks-installed
        - file: /usr/bin/checkfallbacks.py
        - file: /home/lantern/fallbacks-to-check.json
{% else %}
  cron.absent:
    - user: lantern
{% endif %}