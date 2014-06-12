{% macro external_ip(grains) %}{{ grains['ip_interfaces']['eth0'][0] }}{% endmacro %}
