/sbin/reboot:
  cron.present:
    - identifier: reboot
    - user: root
{# Shoot for 4:30 in Beijing and Tehran; let's hope it's OK for other locations. #}
{% if pillar['datacenter'] == 'doams3' %}
    - hour: 1
    - minute: 0
{% else %}
    - hour: 20
    - minute: 30
{% endif %}