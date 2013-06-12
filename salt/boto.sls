# Need to remove the apt-get version because it takes precedence over the
# (more recent) pip version.
boto:
    pkg.removed

# It's crucial that this version is in sync between the cloudmaster and all
# subsequently launched minions because the cloudmaster is passing pickled
# classes to them.  Just `salt-call state.highstate` every time you update this
# and you'll be OK.
boto==2.9.5:
    pip.installed:
        - upgrade: yes
