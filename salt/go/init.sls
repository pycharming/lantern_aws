{% set GOPATH="/home/lantern/go" %}

{{ GOPATH }}:
    file.directory:
        - user: lantern
        - group: lantern
        - mode: 700

go-env-vars:
    file.append:
        - name: /etc/profile
        - text:
            - "export GOPATH={{ GOPATH }}"
            - "export PATH=/usr/local/go/bin:$PATH"
        - require:
            - file: {{ GOPATH }}

install-go:
    cmd.script:
        - source: salt://go/install-go.bash
        - unless: "which go"
        - user: root
        - group: root
        - cwd: /home/lantern
        - require:
            - file: go-env-vars
