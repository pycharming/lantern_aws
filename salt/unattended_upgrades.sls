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
    - watch:
      - debconf: unattended-upgrades
    - env:
        DEBIAN_FRONTEND: noninteractive
        DEBCONF_NONINTERACTIVE_SEEN: "true"
