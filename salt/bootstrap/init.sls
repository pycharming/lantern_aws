# This just creates the directory and copies the file.  Actual user and
# permission management will be done in the `lantern` module.
#
# This goes in a bootstrap module because public proxy port is picked on
# instance creation, and it would be cumbersome to deal with it later.

/etc/lantern:
    file.directory

/etc/lantern/public-proxy-port:
    file.managed:
        - source: salt://bootstrap/public-proxy-port
