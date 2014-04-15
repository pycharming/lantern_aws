include:
    - salt_cloud
    - lockfile

/etc/ufw/applications.d/salt:
    file.managed:
        - source: salt://cloudmaster/ufw-rules
        - user: root
        - group: root
        - mode: 644

'ufw app update Salt ; ufw allow salt':
    cmd.run:
        - require:
            - file: /etc/ufw/applications.d/salt

{% for script_name in ['cloudmaster', 'check_unresponsive_fallbacks'] %}
/home/lantern/{{ script_name }}.py:
    file.managed:
        - source: salt://cloudmaster/{{ script_name }}.py
        - template: jinja
        - user: root
        - group: root
        - mode: 700
    cron.present:
        - user: root
        - require:
            - pip: lockfile
{% endfor %}
