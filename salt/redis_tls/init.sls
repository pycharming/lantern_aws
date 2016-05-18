cert-dirs:
  file.directory:
    - names:
        - /usr/secret/redis
    - user: root
    - group: root
    - mode: 755
    - makedirs: yes
    - recurse:
        - user
        - group
        - mode


{% set files=['garantia_ca.pem', 'garantia_user_private.key', 'garantia_user.crt'] %}

{% for file in files %}

/usr/secret/redis/{{ file }}:
  file.managed:
    - order: 2
    - source: salt://redis_tls/certs/{{ file }}
    - template: jinja
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
    - require:
        - file: cert-dirs

{% endfor %}
