netdata-dependencies:
  pkg.installed:
    - names:
      - git
      - zlib1g-dev
      - gcc
      - make
      - autoconf
      - autogen
      - automake
      - pkg-config

install-netdata:
  cmd.script:
    - source: salt://netdata/install-netdata.bash
    - creates: /etc/netdata-installed
    - require:
        - pkg: netdata-dependencies

/etc/init/netdata.conf:
  file.managed:
    - source: salt://netdata/netdata.conf
        
netdata:
  service.running:
    - enable: yes
    - require:
        - cmd: install-netdata
        - file: /etc/init/netdata.conf
          
          
