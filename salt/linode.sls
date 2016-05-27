linode:
  file.append:
    - name: /etc/environment
    - text: |
        LINODE_APIKEY="{{ pillar['linode_apikey'] }}"
        LINODE_TOKYO_APIKEY="{{ pillar['linode_tokyo_apikey'] }}"
  pip.installed:
    - name: linode-python==1.1.1
