/sbin/reboot:
  cron.absent:
    - identifier: reboot
    - user: root