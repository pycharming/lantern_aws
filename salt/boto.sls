include:
    - pip

boto:
    cmd.run:
        - name: sudo pip install boto==2.5.2
        - require:
            - cmd: pip

