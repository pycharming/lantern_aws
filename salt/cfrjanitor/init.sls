{% from 'install_from_release.sls' import install_from_release %}

{# define cmd: cfrjanitor-installed #}
{{ install_from_release('cfrjanitor', '0.0.18') }}

/usr/bin/cfrjanitor.bash:
    file.managed:
        - source: salt://cfrjanitor/cfrjanitor.bash
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: 700
    cron.present:
        - user: lantern
        - minute: "*/7"
        - require:
            - cmd: cfrjanitor-installed
            - file: /usr/bin/cfrjanitor.bash