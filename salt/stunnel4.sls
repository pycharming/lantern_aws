stunnel4:
  pkg.installed:
    - refresh: True

  service.running:
    - enable: yes
    - watch:
        - file: /etc/default/stunnel4
        - file: /etc/stunnel/*

enable-stunnel:
  file.replace:
    - name: /etc/default/stunnel4
    - pattern: "ENABLED=0"
    - repl: "ENABLED=1"
    - append_if_not_found: yes
    - require:
      - pkg: stunnel4
