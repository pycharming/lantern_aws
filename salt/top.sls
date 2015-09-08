base:
    '*':
        - base_prereqs
        - ulimits
        - pip
        - security
        - lantern_administrators
        - unattended_upgrades
        - boto
        - locales
        - enable_swap
        - timezone
    '*cloudmaster*':
        - salt_cloud
        - cloudmaster
        - cfrjanitor
        - check_vpss
        - checkfallbacks
    'fp-*':
        - apt_upgrade
        - fallback_proxy
    'fl-*':
        - apt_upgrade
        - flashlight
    'wd-*':
        - apt_upgrade
        - waddell
    'ps-*':
        - apt_upgrade
        - peerscanner
    'au-*':
        - apt_upgrade
        - auto_update
