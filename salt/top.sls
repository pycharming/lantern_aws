base:
    '*':
        - base_prereqs
        - ulimits
        - pip
        - security
        - lantern_administrators
        - unattended_upgrades
        - locales
        - enable_swap
        - timezone
        - monitor
    'cm-*':
        - salt_cloud
        - cloudmaster
        - check_vpss
        - checkfallbacks
    'fp-*':
        - lantern_build_prereqs
        - apt_upgrade
        - fallback_proxy