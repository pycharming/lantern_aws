{% for name in 'myles','pants','aranhoide' %}

{{ name }}:
    user.present:
      - gid_from_name: yes
      - home: /home/{{ name }}
      - shell: /bin/bash
      - optional_groups:
        - adm
        - admin
        - dip
        - netdev

/home/{{ name }}:
    file.directory:
      - user: {{ name }}
      - mode: 700
      - require:
        - user: {{ name }}

/home/{{ name }}/.ssh:
    file.directory:
      - user: {{ name }}
      - mode: 700
      - require:
        - user: {{ name }}
        - file: /home/{{ name }}

/etc/sudoers.d/90-{{ name }}:
    file.managed:
      - source: salt://lantern_administrators/nopw_sudoers
      - user: root
      - gid: root
      - mode: 440
      - template: jinja
      - context:
        username: {{ name }}

{{ name }}_ssh:
    ssh_auth.present:
      - user: {{ name }}
      - source: salt://lantern_administrators/{{ name }}.pub_key
      - require:
        - file: /home/{{ name }}/.ssh

{{ name }}_gitsalt_ssh:
    ssh_auth.present:
      - user: gitsalt
      - source: salt://lantern_administrators/{{ name }}.pub_key
      - require:
        - file: /home/gitsalt/.ssh

{% endfor %}
