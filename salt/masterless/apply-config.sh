#!/usr/bin/env bash

SALT_DIR=/srv/salt
DIRTY_FILE=${SALT_DIR}/.dirty

if [[ -f ${DIRTY_FILE} || $1 == "--force" ]]; then
    rm -f ${DIRTY_FILE}
    logger "applying salt configuration updates..."
    PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin salt-call state.highstate 2>&1 | tee /root/salt.log | logger
    logger "done applying salt configuration updates."
    sudo -u lantern touch /home/lantern/.update-done
fi
