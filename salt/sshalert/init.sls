/usr/bin/sshalert.py:
  file.managed:
    - source: salt://sshalert/sshalert.py
    - mode: 755

/etc/ssh/sshd_config:
  file.append:
    - text: "ForceCommand /usr/bin/sshalert.py"
    - require:
       - file: /usr/bin/sshalert.py

reload-sshd:
  service.running:
    # Ubuntu calls this service ssh, not sshd.
    - name: ssh
    - watch:
        - file: /etc/ssh/sshd_config
        - file: /usr/bin/sshalert.py
