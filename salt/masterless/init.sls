include:
    - masterless.forced-apply-config


git:
    pkg.installed

cron:
    pkg.installed

salt:
    group.present

# The master git user controls the git repository where the salt configuration
# is stored.
gitsalt:
    user.present:
      - gid: salt
      - shell: /usr/bin/git-shell
      - require:
        - pkg: git
        - group: salt

/home/gitsalt:
    file.directory:
      - user: gitsalt
      - mode: 700
      - require:
        - user: gitsalt

/home/gitsalt/.ssh:
    file.directory:
      - user: gitsalt
      - mode: 700
      - require:
        - file: /home/gitsalt

# The master git user owns the main salt configuration directory so it can
# overwrite it when the configuration repo changes.
#
# The salt group is given read access so that salt itself can get to the
# current config.
/srv/salt:
    file.directory:
      - user: gitsalt
      - group: salt
      - mode: 750
      - recurse:
        - user
        - group

# The salt configuration repo is stored here.
/home/gitsalt/config:

    file.directory:
      - user: gitsalt
      - mode: 700
      - require:
        - file: /home/gitsalt
      # I need to run _after_ the git state because it overwrites the
      # permissions I set.
      - watch:
        - git: /home/gitsalt/config

    git.present:
      - runas: gitsalt
      - force: yes
      - require:
        - user: gitsalt
        - pkg: git
        - file: /home/gitsalt

/home/gitsalt/config/hooks/post-receive:
    file.managed:
      - source: salt://masterless/post-receive
      - user: gitsalt
      - mode: 700
      - require:
        - git: /home/gitsalt/config

/root/apply-config.sh:
    file.managed:
      - source: salt://masterless/apply-config.sh
      - user: root
      - mode: 700
    cron: 
      - present

