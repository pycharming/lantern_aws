{% for name in 'myles','pants','aranhoide','leahxschmidt','lantern','invsrvlauncher' %}

{{ name }}:
    user.present:
      - gid_from_name: yes
      - home: /home/{{ name }}
      - shell: /bin/bash

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

{% endfor %}

{% for admin in 'myles','pants','aranhoide','leahxschmidt' %}
{% for role in admin,'lantern','invsrvlauncher' %}
{{ admin }}_{{ role }}_ssh:
    ssh_auth.present:
      - user: {{ role }}
      - source: salt://lantern_administrators/{{ admin }}.pub_key
      - require:
        - file: /home/{{ role }}/.ssh
{% endfor %}
{% endfor %}
