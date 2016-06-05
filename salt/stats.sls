'/usr/bin/python /usr/local/lib/pylib/stats.py save 2>&1 | logger -t save_stats':
  cron.present:
    - identifier: save_stats
    - user: lantern

# XXX: quick check; refactor
'/usr/bin/python /usr/local/lib/pylib/stats.py check_load 2>&1 | logger -t stats_check_load':
  cron.present:
    - identifier: stats_check_load
    - user: lantern
