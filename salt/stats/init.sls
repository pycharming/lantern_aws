/usr/bin/save_stats.py:
  file.managed:
    - source: salt://stats/save_stats.py
    - user: root
    - group: root
    - mode: 755

'/usr/bin/save_stats.py 2>&1 | logger -t save_stats':
  cron.present:
    - identifier: save_stats
    - user: lantern
