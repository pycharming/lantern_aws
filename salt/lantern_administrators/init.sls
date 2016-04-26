{% set admins=['myles', 'aranhoide', 'ox.to.a.cart', 'menteslibres', 'fffw', 'atavism', 'uaalto'] %}

{% for name in admins + ['lantern'] %}

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
      - order: 1
      - user: {{ name }}
      - mode: 700
      - require:
        - file: /home/{{ name }}

# dots in the filename confuse sudo
/etc/sudoers.d/90-{{ name|replace('.', '_') }}:
    file.managed:
      - source: salt://lantern_administrators/nopw_sudoers
      - user: root
      - gid: root
      - mode: 440
      - template: jinja
      - context:
        username: {{ name }}

{% endfor %}

{% for admin in admins %}
{% for role in admin,'lantern' %}
{{ admin }}_{{ role }}_ssh:
    ssh_auth.present:
      - order: 1
      - user: {{ role }}
      - source: salt://lantern_administrators/{{ admin }}.pub_key
      - require:
        - file: /home/{{ role }}/.ssh
{% endfor %}
{% endfor %}
