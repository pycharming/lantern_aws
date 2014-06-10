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
        - enable_swap
        - timezone
    'cloudmaster':
        - lantern_build_prereqs
        - salt_master
        - salt_cloud
        - cloudmaster
    'fp-*':
        - lantern_build_prereqs
        - apt_upgrade
        - fallback_proxy
    'wb-*':
        - lantern_build_prereqs
        - wrapper_builder
    'fl-*':
        - apt_upgrade
        - flashlight
