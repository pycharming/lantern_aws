env:
  file.append:
    - name: /etc/environment
    - text: |
        CM={{ pillar['cloudmaster_name'] }}
        SLACK_WEBHOOK_URL={{ pillar['slack_webhook_url'] }}
