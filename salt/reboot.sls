/sbin/reboot:
  cron.present:
    - identifier: reboot
    - user: root
{# Shoot for 4:30 in Beijing and Tehran; let's hope it's OK for other locations. #}
{% if pillar['datacenter'] == 'vltok1' %}
    - hour: 20
    - minute: 30
{% else %}
    - hour: 1
    - minute: 0
{% endif %}