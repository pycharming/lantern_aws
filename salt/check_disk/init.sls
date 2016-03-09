/usr/bin/check_disk.py:
  file.managed:
    - mode: 755
    - source: salt://check_disk/check_disk.py

"/usr/bin/check_disk.py 2>&1 | logger -t check_disk":
  cron.present:
    - user: root
    - identifier: check_disk
    - require:
        - file: /usr/bin/check_disk.py
