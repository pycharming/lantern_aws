dcenv:
  file.append:
    - name: /etc/environment
      - text: |
        DC={{ pillar['datacenter'] }}
        CM={{ pillar['cloudmaster_name'] }}