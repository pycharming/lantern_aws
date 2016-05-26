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

disable-password-authentication:
  file.replace:
    - name: /etc/ssh/sshd_config
    - pattern: "^PasswordAuthentication\\s+\\w+"
    - repl: "PasswordAuthentication no"
    - append_if_not_found: yes

disable-challenge-response-authentication:
  file.replace:
    - name: /etc/ssh/sshd_config
    - pattern: "^ChallengeResponseAuthentication\\s+\\w+"
    - repl: "ChallengeResponseAuthentication no"
    - append_if_not_found: yes

reload-sshd-on-password-disable:
  service.running:
    - name: ssh
    - watch:
        - file: disable-password-authentication
        - file: disable-challenge-response-authentication

# On initial launch, our VPS providers initialize the `root` user account with a
# SSH key (called `cloudmaster`) so we can perform initial setup. As soon as we
# first run Salt configuration, this key becomes unnecessary, so let's remove
# it.
# XXX: disabled since this often prevents proxies from completing setup.  I'll
#      make cloudmasters delete this one on successful setup.
#/root/.ssh/authorized_keys:
#  file.replace:
#    - pattern: "ssh-rsa \\S+ lanterncyborg@gmail\\.com\n"
#    - repl: ""
#    # Without this line salt-cloud setup will fail with a SSH login error.
#    - order: last
