some-pip:
  cmd.run:
    - name: "apt-get install -q python-pip"
    - unless: "which pip"

# Salt v2015.8.8.2 requires a newer version than the one in Ubuntu 14.04, but it
# breaks with the newest one as of this writing.
# We can't use salt's own pip state because it requires an "importable" pip, which
# apparently the one that comes in Ubuntu 14.04 isn't.
pip8.1.1:
  cmd.run:
    - name: 'pip install --upgrade --force pip==8.1.1'
    - unless: '[ $(pip --version | cut -d " " -f 2) = "8.1.1" ]'
    - order: 0
    - require:
        - cmd: some-pip
