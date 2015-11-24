env:
  file.append:
    - name: /etc/environment
    - text: |
        CM={{ pillar['cloudmaster_name'] }}