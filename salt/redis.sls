python-hiredis:
  pkg.installed

python-redis:
  pkg.installed:
    - require:
        - pkg: python-hiredis