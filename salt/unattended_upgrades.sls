update-notifier-common:
    pkg.installed

auto-reboot:
  file.replace:
    - name: '/etc/apt/apt.conf.d/50unattended-upgrades'
    - pattern: '//Unattended-Upgrade::Automatic-Reboot "false";'
    - repl: 'Unattended-Upgrade::Automatic-Reboot "true";'
    - append_if_not_found: yes

auto-reboot-time:
  file.replace:
    - name: '/etc/apt/apt.conf.d/50unattended-upgrades'
    - pattern: '(//)?Unattended-Upgrade::Automatic-Reboot-Time ".+:.+";'
{# Shoot for 4:30 in Beijing and Tehran; let's hope it's OK for other locations. #}
{% if pillar['datacenter'] == 'doams3' %}
    - repl: 'Unattended-Upgrade::Automatic-Reboot-Time "01:00";'
{% else %}
    - repl: 'Unattended-Upgrade::Automatic-Reboot-Time "20:30";'
{% endif %}
    - append_if_not_found: yes

unattended-upgrades:
  pkg.installed: []
  debconf.set:
    - data:
        'unattended-upgrades/enable_auto_updates':
          type: boolean
          value: "true"
  cmd.wait:
    - name: "dpkg-reconfigure unattended-upgrades"
    - require:
      - pkg: unattended-upgrades
      - pkg: update-notifier-common
    - watch:
      - debconf: unattended-upgrades
      - file: auto-reboot
      - file: auto-reboot-time
    - env:
        DEBIAN_FRONTEND: noninteractive
        DEBCONF_NONINTERACTIVE_SEEN: "true"
