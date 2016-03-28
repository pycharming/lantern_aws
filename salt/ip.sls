{% macro external_ipv4(grains) %}{{ grains['ip4_interfaces']['eth0'][0] }}{% endmacro %}
{% macro internal_ipv4(grains) %}{{ grains['ip4_interfaces']['eth1'][0] }}{% endmacro %}
{% macro external_ipv6(grains) %}{{ grains['ip6_interfaces']['eth0'][0] }}{% endmacro %}
{% macro internal_ipv6(grains) %}{{ grains['ip6_interfaces']['eth1'][0] }}{% endmacro %}
