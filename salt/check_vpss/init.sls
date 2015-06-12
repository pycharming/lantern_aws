python-digitalocean:
  pip.installed

vultr:
  pip.installed

/home/lantern/do_vpss:
  file.managed:
    - source: salt://check_vpss/do_vpss
    - user: lantern
    - group: lantern
    - mode: 644
        
/home/lantern/vultr_vpss:
  file.managed:
    - source: salt://check_vpss/vultr_vpss
    - user: lantern
    - group: lantern
    - mode: 644
      
/home/lantern/check_vpss.py:
  file.managed:
    - source: salt://check_vpss/check_vpss.py
    - template: jinja
    - user: lantern
    - group: lantern
    - mode: 755

{% if grains.get('controller', pillar.get('controller', 'not-production')) == grains.get('production_controller', 'lanternctrl1-2') %}
/home/lantern/check_vpss.py 2>&1 | /usr/bin/logger -t check_vpss:
  cron.present:
    - hour: 2
    - minute: 1
    - user: lantern
    - require:
        - pip: python-digitalocean
        - pip: vultr
        - file: /home/lantern/check_vpss.py
        - file: /home/lantern/do_vpss
        - file: /home/lantern/vultr_vpss
{% endif %}