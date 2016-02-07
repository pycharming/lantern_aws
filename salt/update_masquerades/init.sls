/home/lantern/update_masquerades/proxiedsites:
  file.directory:
    - user: lantern
    - group: lantern
    - dir_mode: 755
    - makedirs: True
    - recurse:
      - user
      - group
      - mode

{% set nontemplate_files=[
    ('/home/lantern/update_masquerades/', 'genconfig', 'genconfig', 'lantern', 744),
    ('/home/lantern/update_masquerades/', 'genconfig.bash', 'genconfig.bash', 'lantern', 744),
    ('/home/lantern/update_masquerades/', 'cfg2redis.py', 'cfg2redis.py', 'lantern', 744),
    ('/home/lantern/update_masquerades/', 'blacklist.txt', 'blacklist.txt', 'lantern', 644),
    ('/home/lantern/update_masquerades/', 'masquerades.txt', 'masquerades.txt', 'lantern', 644),
    ('/home/lantern/update_masquerades/', 'fallbacks.yaml', 'fallbacks.yaml', 'lantern', 644),
    ('/home/lantern/update_masquerades/', 'cloud.yaml.tmpl', 'cloud.yaml.tmpl', 'lantern', 644),
    ('/home/lantern/update_masquerades/proxiedsites/', 'original.txt', 'original.txt', 'lantern', 644),
    ('/home/lantern/update_masquerades/proxiedsites/', 'firefly-blacklist.txt', 'firefly-blacklist.txt', 'lantern', 644),
    ('/home/lantern/update_masquerades/proxiedsites/', 'google_domains.txt', 'google_domains.txt', 'lantern', 644),
] %}

{% for dir,dst_filename,src_filename,user,mode in nontemplate_files %}
{{ dir+dst_filename }}:
    file.managed:
        - source: salt://update_masquerades/{{ src_filename }}
        - user: {{ user }}
        - group: {{ user }}
        - mode: {{ mode }}
        - require:
            - file: /home/lantern/update_masquerades/proxiedsites
{% endfor %}

'cd /home/lantern/update_masquerades/ && ./genconfig.bash':
  cron.present:
    - identifier: update_masquerades
    - user: lantern
    - minute: 1
    - hour: 21