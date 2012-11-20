unattended-upgrades:
    pkg.installed

{% for filename in '10periodic','50unattended-upgrades' %}
/etc/apt/apt.conf.d/{{ filename }}:
    file.managed:
      - source: salt://automatic_updates/{{ filename }}
      - user: root
      - gid: root
      - mode: 600
      - require:
        - package: unattended-upgrades

{% endfor %}
