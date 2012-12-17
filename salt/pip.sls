python-setuptools:
    pkg.installed

pip:
    cmd.run:
        - name: test "$(which pip)" || sudo easy_install pip
        - require:
            - pkg: python-setuptools
