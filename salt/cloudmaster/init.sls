include:
    - salt_cloud

/home/lantern/cloudmaster.py:
    file.managed:
        - source: salt://cloudmaster/cloudmaster.py
        - template: jinja
        - user: lantern
        - group: lantern
        - mode: 700
    cron.present:
        - user: lantern
        - require:
            - pip: lockfile==0.9.1
            - cmd: salt-cloud

lockfile==0.9.1:
    pip.installed
