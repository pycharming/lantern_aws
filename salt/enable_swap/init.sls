enable-swap:
    cmd.script:
        - source: salt://enable_swap/make-swap.bash
        - unless: "[ $(swapon -s | wc -l) -gt 1 ]"
        - user: root
        - group: root
