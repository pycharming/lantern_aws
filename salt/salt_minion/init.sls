/etc/init.d/salt-minion:
    file.managed:
        - user: root
        - group: root
        - source: salt://salt_minion/salt-minion.init
        - mode: 700

salt-minion:
    # Remove apt package so we don't upgrade automatically.
    pkg.removed: []
    service.running:
        - enable: yes
        - watch:
            - file: /etc/init.d/salt-minion
            - pip: salt

remove-old-salt-install-dir:
    cmd.run:
        - name: 'rm -rf /tmp/pip-build-root/salt'

# This preliminary step is required so we don't upgrade recursively unless
# necessary. pip: salt will take care of really necessary dependent installs
# or upgrades.  See
# http://www.pip-installer.org/en/latest/cookbook.html#non-recursive-upgrades
salt-nodeps:
    pip.installed:
        - name: salt=={{ pillar['salt_version'] }}
        - upgrade: yes
        - no_deps: yes
        - require:
            - cmd: remove-old-salt-install-dir

salt:
    # Use pip package so we maintain control over installed versions.
    pip.installed:
        # Not as tautological as it looks.  bin/update.py may change this on
        # the cloudmaster, and then a subsequent state.highstate applies the
        # upgrade.
        - name: salt=={{ pillar['salt_version'] }}
        - require:
            - pip: salt-nodeps
