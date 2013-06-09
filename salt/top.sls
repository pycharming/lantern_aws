base:
    '*':
        - base_prereqs
        - security
        - lantern_administrators
        - unattended_upgrades
    'cloudmaster':
        - salt_cloud
        - cloudmaster
    #DRY warning: cloudmaster/cloudmaster.py
    'fp-*':
        - fallback_proxy
