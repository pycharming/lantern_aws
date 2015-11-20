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
    'cm-doams3':
        - vps_sanity_checks
        - check_vpss
    'cm-*':
        - salt_cloud
        - cloudmaster
        - checkfallbacks
    'fp-*':
        - lantern_build_prereqs
        - apt_upgrade
{% if pillar['datacenter'] == 'doams3' %}
        - http_proxy
{% else %}
        - ats
{% endif %}