digitalocean:
  file.append:
    - name: /etc/environment
    - text: "DO_TOKEN={{ pillar['do_token'] }}"
  pip.installed:
    - name: python-digitalocean==1.6