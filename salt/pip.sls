some-pip:
  cmd.run:
    - name: "apt-get install python-pip"
    - unless: "which pip"

# Salt v2015.8.8.2 requires a newer version than the one in Ubuntu 14.04, but it
# breaks with the newest one as of this writing.
pip==8.1.1:
  pip.installed:
    - order: 0
    - require:
        - cmd: some-pip
