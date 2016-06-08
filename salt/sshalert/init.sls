ssh-whitelist-query-token-env-var:
  file.replace:
    - name: /etc/environment
    - pattern: "^SSH_WHITELIST_QUERY_TOKEN=.*$"
    - repl: SSH_WHITELIST_QUERY_TOKEN="{{ pillar['ssh_whitelist_query_token'] }}"
    - append_if_not_found: yes

/usr/bin/sshalert.py:
  file.managed:
    - source: salt://sshalert/sshalert.py
    - mode: 755

/etc/ssh/sshd_config:
  file.append:
    - text: "ForceCommand /usr/bin/sshalert.py"
    # prevent spurious logs on VPS creation.
    - order: last
    - require:
       - file: /usr/bin/sshalert.py

reload-sshd:
  service.running:
    # Ubuntu calls this service ssh, not sshd.
    - name: ssh
    - watch:
        - file: /etc/ssh/sshd_config
        - file: /usr/bin/sshalert.py
