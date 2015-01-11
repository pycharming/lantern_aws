pip-prereqs:
    pkg.installed:
        - names:
           - python
           - python-support
           - python-pkg-resources
           - python-crypto
           - python-m2crypto
           - dctrl-tools
           - python-markupsafe
           - debconf-utils
           - python-pip

# New pip needs an updated setuptools.
setuptools:
    cmd.run:
        - name: "pip install --upgrade setuptools"

pip:
    cmd.run:
        - name: "pip install --upgrade pip && hash -r"
        - order: 1
        # The apt-get version of pip installs to /usr/bin/pip instead.
        - unless: "[ $(which pip) == /usr/local/bin/pip ]"
        - require:
            - pkg: pip-prereqs
            - cmd: setuptools
