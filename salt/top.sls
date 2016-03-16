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
        - reboot
        - pylib
        - env
        - stats
        - logrotate
        - check_disk
    'cm-vlfra1':
        - vps_sanity_checks
        - check_vpss
        - update_masquerades
    'cm-*':
        - salt_cloud
        - cloudmaster
        - checkfallbacks
    'fp-*':
        - lantern_build_prereqs
        - apt_upgrade
        - http_proxy
    'pubsub-*':
        - pubsub
