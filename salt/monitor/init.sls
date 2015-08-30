{% from 'ip.sls' import external_ip %}

monitor:
  service.running:
    - name: collectd
    - enable: yes
    - require:
      - pkg: collectd
    - watch:
      - file: collectd.conf

collectd:
  pkg.installed:
    - name: collectd

collectd.conf:
  file.managed:
    - name: /etc/collectd/collectd.conf
    - source: salt://monitor/collectd.conf
    - template: jinja
    - user: root
    - group: root
    - mode: 644
    - require:
      - pkg: collectd
