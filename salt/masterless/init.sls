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
      - group: {{ salt['file.group_to_gid']('salt') }}
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

# Dummy crontab entry to work around a bug in Salt.  First crontab entry that
# Salt adds will not be recognized by it as being managed, because it appears
# above the comment that Salt places in the crontab for this purpose.  Because
# of this, it will be added twice to the crontab.
#
# https://github.com/saltstack/salt/issues/2638
#
# While this doesn't get fixed, I just add an entry that runs rarely and does
# nothing, and I make sure it's the first one to be added, by making the
# others depend on it.
dummy-cronjob:
    cron.present:
        - name: ": 2>&1 > /dev/null"  # for good measure  :)
        - minute: 1
        - hour: 1
        - daymonth: 1
        - month: 1

/root/apply-config.sh:
    file.managed:
      - source: salt://masterless/apply-config.sh
      - user: root
      - mode: 700
    cron.present:
      - require:
        - file: /root/apply-config.sh
        - cron: dummy-cronjob

{% set minute = salt['cmd.run']("python -c 'import random, socket; random.seed(socket.gethostname()); print random.randint(1, 59),'") %}

"/root/apply-config.sh --force":
    cron.present:
        - minute: {{ minute }}
        - require:
            - cron: /root/apply-config.sh
