{% macro external_ip(grains) %}{{ grains['ip_interfaces']['eth0'][0] }}{% endmacro %}
{% macro internal_ip(grains) %}{{ grains['ip_interfaces']['eth1'][0] }}{% endmacro %}
