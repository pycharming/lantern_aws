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
        - locales
        - lantern_build_prereqs
        - enable_swap
        - timezone
    'cloudmaster':
        - salt_master
        - salt_cloud
        - cloudmaster
    #DRY warning: cloudmaster/cloudmaster.py
    'fp-*':
        - apt_upgrade
        - fallback_proxy
