{% from 'ip.sls' import external_ip %}

monitor:
  service.running:
    - name: collectd
    - enable: yes
    - require:
      - pkg: collectd

collectd:
  pkg.installed:
    - name: collectd==5.4.1

/etc/collectd/collectd.conf
  file.managed:
    - source: salt://monitoring/collectd.conf
    - template: jinja
    - context:
        external_ip: {{ external_ip(grains) }}

