{% for name in 'myles','pants','aranhoide','leahxschmidt','lantern','invsrvlauncher' %}

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

{% endfor %}

{% for admin in 'myles','pants','aranhoide','leahxschmidt' %}
{% for role in admin,'gitsalt','lantern','invsrvlauncher' %}

{{ admin }}_{{ role }}_ssh:
    ssh_auth.present:
      - user: {{ role }}
      - source: salt://lantern_administrators/{{ admin }}.pub_key
      - require:
        - file: /home/{{ role }}/.ssh


{% endfor %}
{% endfor %}

# invsrvlauncher needs access to these accounts in order to initialize new
# instances.
{% for role in 'lantern','gitsalt' %}
invsrvlauncher_{{ role }}_ssh:
    ssh_auth.present:
      - user: {{ role }}
      - source: salt://lantern_administrators/invsrvlauncher.pub_key
      - require:
        - file: /home/{{ role }}/.ssh
{% endfor %}
