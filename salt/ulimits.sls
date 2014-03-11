/etc/security/limits.conf:
    file.append:
        - text:
            - "* soft core unlimited"
            - "* hard core unlimited"
            - "* soft nofile 128000"
            - "* hard nofile 128000"
        - order: 1
