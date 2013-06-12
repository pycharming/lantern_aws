fail2ban:
    pkg.installed:
        - order: 2

ufw:
    pkg.installed:
        - order: 2
    service.running:
        - order: 2
        - enabled: yes
        - require:
            - pkg: ufw

# Don't lock ourselves out of the box.
'ufw allow openssh':
    cmd.run:
        - order: 2
        - require:
            - service: ufw
