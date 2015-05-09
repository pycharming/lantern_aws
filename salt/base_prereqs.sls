base-packages:
    pkg.installed:
        - order: 1
        - names:
            - python-software-properties
            - curl
            - python-pycurl
            - git
            - mailutils
        - reload_modules: yes
