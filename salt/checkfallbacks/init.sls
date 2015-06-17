{% from 'install_from_release.sls' import install_from_release %}

{# define cmd: checkfallbacks-installed #}
{{ install_from_release('checkfallbacks', '0.0.20') }}

/home/lantern/fallbacks-to-check.json:
  file.managed:
    - source: salt://checkfallbacks/fallbacks-to-check.json
    - user: lantern
    - group: lantern
    - mode: 644

/usr/bin/checkfallbacks.py:
  file.managed:
    - source: salt://checkfallbacks/checkfallbacks.py
    - user: root
    - group: root
    - mode: 755

"/usr/bin/checkfallbacks.py | logger -t checkfallbacks":
{% if grains.get('controller', pillar.get('controller', 'not-production')) == grains.get('production_controller', 'lanternctrl1-2') %}
  cron.present:
    - minute: '*/11'
    - user: lantern
    - require:
        - cmd: checkfallbacks-installed
        - file: /usr/bin/checkfallbacks.py
        - file: /home/lantern/fallbacks-to-check.json
{% else %}
  cron.absent:
    - user: lantern
{% endif %}