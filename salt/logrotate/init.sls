/etc/cron.daily/logrotate:
  file.absent

/etc/cron.hourly/logrotate:
  file.managed:
    - source: salt://logrotate/logrotate.cron
    - mode: 755

/etc/logrotate.d/rsyslog:
  file.managed:
    - source: salt://logrotate/rsyslog

/etc/logrotate.d/upstart:
  file.managed:
    - source: salt://logrotate/upstart
