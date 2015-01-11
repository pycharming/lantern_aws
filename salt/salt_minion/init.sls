salt-minion:
    # Remove apt package so we don't upgrade automatically.
    pkg.removed: []
    service.running:
        - enable: yes
        - watch:
            - pip: salt
            - pip: salt-minion-executable

remove-old-salt-install-dir:
    cmd.run:
        - name: 'rm -rf /tmp/pip-build-root/salt'

# pip will be satisfied with a preexisting salt even if it doesn't include
# a proper salt-minion.  This may be introduced by bootstrap scripts.  Here we
# check for and correct this.
salt-minion-executable:
    pip.installed:
        - name: salt=={{ pillar['salt_version'] }}
        - upgrade: yes
        - force_reinstall: yes
        - unless: 'which salt-minion'
        - require:
            - cmd: remove-old-salt-install-dir
            # Prevent the salt-minion removal from happening after this.
            - pkg: salt-minion

salt:
    # Use pip package so we maintain control over installed versions.
    pip.installed:
        # Not as tautological as it looks.  bin/update.py may change this on
        # the cloudmaster, and then a subsequent state.highstate applies the
        # upgrade.
        - name: salt=={{ pillar['salt_version'] }}
        - require:
            - pkg: salt-prereqs

# In theory this is only required for salt-cloud, but now that salt-cloud is
# a part of the salt project this requirement seems to apply even if you don't
# use any salt-cloud functionality.
#apache-libcloud:
#    pip.installed:
#        - upgrade: yes

salt-prereqs:
    pkg.installed:
        - names:
            - swig
            - libssl-dev
            - python-dev
            - libzmq3-dev
            # For some reason this was required in cloudmaster1-2, but not in
            # my test cloudmaster.  -aranhoide
            - python-libcloud

