base-packages:
    pkg.installed:
        - order: 1
        - names:
            - python-software-properties
            - git

some-pip:
    cmd.run:
        - name: "apt-get install python-pip -y"
        - unless: "which pip"

the-right-pip:
    cmd.run:
        - name: "pip install --upgrade pip && hash -r"
        # The apt-get version of pip installs to /usr/bin/pip instead.
        - unless: "[ $(which pip) == /usr/local/bin/pip ]"
        - order: 1
        - require:
            - cmd: some-pip
