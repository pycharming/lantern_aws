base:
    '*':
        - base_prereqs
        - pip
        - security
        - lantern_administrators
        - unattended_upgrades
        - boto
    'cloudmaster':
        - salt_cloud
        - cloudmaster
    #DRY warning: cloudmaster/cloudmaster.py
    'fp-*':
        - apt_upgrade
        - fallback_proxy
