base:
    '*':
        - salt_minion
        - base_prereqs
        - ulimits
        - pip
        - security
        - lantern_administrators
        - unattended_upgrades
        - boto
    'cloudmaster':
        - salt_master
        - salt_cloud
        - cloudmaster
    #DRY warning: cloudmaster/cloudmaster.py
    'fp-*':
        - apt_upgrade
        - fallback_proxy
