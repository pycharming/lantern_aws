base:
    '*':
        - base_prereqs
        - security
        - lantern_administrators
        - unattended_upgrades
    'cloudmaster':
        - lantern_build_prereqs
        - salt_cloud
        - cloudmaster
