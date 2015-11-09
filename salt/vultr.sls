vultr:
  file.append:
    - name: /etc/environment
    - text: "VULTR_APIKEY={{ pillar['vultr_apikey'] }}"
  pip.installed:
    - name: vultr==0.1.2