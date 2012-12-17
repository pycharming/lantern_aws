include:
    - pip

{% for module in 'dnspython','sleekxmpp','pyasn1','pyasn1-modules' %}

{{ module }}:
    cmd.run:
        - name: sudo pip install {{ module }}
        - require:
            - cmd: pip

{% endfor %}
