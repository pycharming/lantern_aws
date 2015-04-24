{% macro install_from_release(name, version) %}

{{ name }}-installed:
   cmd.run:
       - name: 'curl -L https://github.com/getlantern/lantern/releases/download/{{ version }}/{{ name }}_linux_amd64 -o {{ name }} && chmod a+x {{ name }} && mv {{ name }} /usr/bin/'
       - cwd: /tmp
       - user: root

{% endmacro %}