apt-upgrade:
    cmd.run:
        - name: "export DEBIAN_FRONTEND=noninteractive && apt-get update && apt-get upgrade -y -o DPkg::Options::=--force-confold && touch /root/apt_updated"
        - unless: "[ -e /root/apt_updated ]"
        - user: root
        - group: root
        - order: 1
