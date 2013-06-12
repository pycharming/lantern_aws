some-pip:
    cmd.run:
        - name: "apt-get install python-pip -y"
        - unless: "which pip"

the-right-pip:
    cmd.run:
        - name: "pip install --upgrade pip && hash -r"
        - order: 1
        # The apt-get version of pip installs to /usr/bin/pip instead.
        - unless: "[ $(which pip) == /usr/local/bin/pip ]"
        - require:
            - cmd: some-pip
