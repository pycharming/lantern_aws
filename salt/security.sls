fail2ban:
    pkg.removed:
        - order: 2

ufw:
    pkg.installed:
        - order: 2
    service.running:
        - order: 2
        - enable: yes
        - require:
            - pkg: ufw

# Enable ufw (it seems the salt state won't do this by itself), but don't lock
# ourselves out of the box.
'ufw allow openssh && echo y | ufw enable':
    cmd.run:
        - order: 2
        - require:
            - service: ufw
