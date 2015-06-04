include:
    - proxy_ufw_rules

{% from 'install_from_release.sls' import install_from_release %}

{% for name in 'waddell_pk.pem', 'waddell_cert.pem' %}
/home/lantern/{{ name }}:
    file.managed:
        - source: salt://waddell/{{ name }}
        - user: lantern
        - group: lantern
        - mode: 600
{% endfor %} 

{# define cmd: waddel-installed #}
{{ install_from_release('waddell', '0.0.4') }}

waddell-upstart-script:
    file.managed:
        - name: /etc/init/waddell.conf
        - source: salt://waddell/waddell.conf
        - template: jinja
        - user: root
        - group: root
        - mode: 644
        - require:
            - cmd: waddell-installed

waddell-service-registered:
    cmd.run:
        - name: 'initctl reload-configuration'
        - watch:
            - file: waddell-upstart-script

waddell:
    service.running:
        - enable: yes
        - require:
            # All but the last requirement are redundant, only for robustness.
            - cmd: ufw-rules-ready
            - cmd: waddell-service-registered
            - file: /home/lantern/waddell_pk.pem
            - file: /home/lantern/waddell_cert.pem
        - watch:
            - cmd: waddell-installed