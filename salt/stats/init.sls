/usr/bin/stats.py:
  file.managed:
    - source: salt://stats/stats.py
    - user: root
    - group: root
    - mode: 755

'/usr/bin/stats.py save 2>&1 | logger -t save_stats':
  cron.present:
    - identifier: save_stats
    - user: lantern
