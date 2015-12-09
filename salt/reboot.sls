# We used to have unconditional reboots every day. We've since changed this so
# reboot only happens as required by unattended upgrades.
/sbin/reboot:
  cron.absent:
    - identifier: reboot
    - user: root