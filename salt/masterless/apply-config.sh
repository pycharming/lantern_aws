#!/usr/bin/env bash

SALT_DIR=/srv/salt
DIRTY_FILE=${SALT_DIR}/.dirty

if [[ -f ${DIRTY_FILE} || $1 == "--force" ]]; then
    rm -f ${DIRTY_FILE}
    logger "applying salt configuration updates..."
    /usr/bin/salt-call -l debug state.highstate 2>&1 | tee /root/salt.log | logger
fi
