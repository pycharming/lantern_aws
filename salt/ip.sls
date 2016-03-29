{# It's a happy coincidence that currently in both DO and Vultr eth0 is the
public interface and eth1 is the one for private networking. Also, public
addresses are listed before private ones in both. We should check these
assumptions for every new provider we add. #}
{% macro external_ipv4(grains) %}{{ grains['ip4_interfaces']['eth0'][0] }}{% endmacro %}
{% macro internal_ipv4(grains) %}{{ grains['ip4_interfaces']['eth1'][0] }}{% endmacro %}
{% macro external_ipv6(grains) %}{{ grains['ip6_interfaces']['eth0'][0] }}{% endmacro %}
{% macro internal_ipv6(grains) %}{{ grains['ip6_interfaces']['eth1'][0] }}{% endmacro %}
