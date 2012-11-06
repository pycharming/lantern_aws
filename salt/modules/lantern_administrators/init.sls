{% for name in 'myles','pants','aranhoide' %}

{{ name }}:
    user.present:
      - gid_from_name: yes
      - home: /home/{{ name }}
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

{% for auth_name in name,'gitsalt' %}
{{ auth_name }}_ssh:
    ssh_auth.present:
      - user: {{ auth_name }}
      - source: salt://lantern_administrators/{{ name }}.pub_key
      - enc: ssh-rsa
{% endfor %}

{% endfor %}
