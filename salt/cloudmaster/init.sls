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

{% set scripts = [('cloudmaster', '1'),
                  ('alert_fallbacks_failing_to_proxy', '8')] %}
{% if grains['controller'] == grains['production_controller'] %}
    {% set scripts=scripts + [('check_unresponsive_fallbacks', '15')] %}
{% endif %}
{% for script_name, minutes in scripts %}
/home/lantern/{{ script_name }}.py:
    file.managed:
        - source: salt://cloudmaster/{{ script_name }}.py
        - template: jinja
        - user: root
        - group: root
        - mode: 700
    cron.present:
        - user: root
        - minute: "*/{{ minutes }}"
        - require:
            - pip: lockfile
{% endfor %}
