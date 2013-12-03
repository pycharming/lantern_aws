/etc/security/limits.conf:
    file.append:
        - text: "*\t\tsoft\tcore\t\tunlimited"
        - order: 1
