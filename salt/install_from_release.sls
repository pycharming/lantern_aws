{% macro install_from_release(name, version, sha) %}

{{ name }}-installed:
   cmd.run:
       - name: 'curl -L -f https://github.com/getlantern/lantern/releases/download/{{ version }}/{{ name }}_linux_amd64 -o {{ name }} && chmod a+x {{ name }} && mv {{ name }} /usr/bin/'
       - unless: '[ $(shasum /usr/bin/{{ name }} | cut -d " " -f 1) = {{ sha }} ]'
       - cwd: /tmp
       - user: root

{% endmacro %}
