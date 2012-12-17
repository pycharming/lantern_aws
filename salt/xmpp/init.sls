include:
    - pip

{% for module in 'requests','dnspython','sleekxmpp','pyasn1','pyasn1-modules' %}

{{ module }}:
    cmd.run:
        - name: sudo pip install {{ module }}
        - require:
            - cmd: pip

{% endfor %}

# Simplify dependencies with bogus command that depends on everything else in
# this module.
xmpp:
    cmd.run:
        - name: ":"
        - require:
{% for module in 'requests','dnspython','sleekxmpp','pyasn1','pyasn1-modules' %}
            - cmd: {{ module }}
{% endfor %}
