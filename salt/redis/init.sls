{% set nontemplate_files=[
    ('/etc/lantern/redis/', 'garantia_ca.pem', 'redis/garantia_ca.pem', 'root', 644),
    ('/etc/lantern/redis/secondary-redis/', 'garantia_user_private.key', 'redis/secondary-redis/garantia_user_private.key', 'root', 644),
    ('/etc/lantern/redis/secondary-redis/', 'garantia_user.crt', 'redis/secondary-redis/garantia_user.crt', 'root', 644)] %}

redis-env:
  file.append:
    - name: /etc/environment
    - text: "REDIS_URL={{ pillar['cfgsrv_redis_url'] }}"

python-hiredis:
  pkg.installed

python-redis:
  pkg.installed:
    - require:
        - pkg: python-hiredis

{% for dir,dst_filename,src_filename,user,mode in nontemplate_files %}
{{ dir+dst_filename }}:
    file.managed:
        - source: salt://redis/{{ src_filename }}
        - user: {{ user }}
        - group: {{ user }}
        - mode: {{ mode }}
        - require:
            - file: fp-dirs
{% endfor %}
