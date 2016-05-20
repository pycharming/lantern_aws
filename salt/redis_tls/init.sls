{% set files=['all_cas.pem', 'garantia_user_private.key', 'garantia_user.crt', 'redis.getlantern.org/fullchain.pem', 'redis.getlantern.org/cert.pem', 'redis.getlantern.org/privkey.pem'] %}

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

{% endfor %}
