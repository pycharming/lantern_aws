dcenv:
  file.append:
    - name: /etc/environment
    - text: "DC={{ pillar['datacenter'] }}"