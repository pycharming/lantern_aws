# Perl complains to me unless I configure these.
"locale-gen en_US en_US.UTF-8 gl_ES.UTF-8 && dpkg-reconfigure locales && touch /root/locales-configured":
    cmd.run:
        - unless: "[ -e /root/locales-configured ]"
