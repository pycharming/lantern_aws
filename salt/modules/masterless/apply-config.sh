#!/usr/bin/env bash

PUPPET_DIR=<%= puppet_config_dir %>
DIRTY_FILE=${PUPPET_DIR}/.dirty

if [[ -f ${DIRTY_FILE} || $1 == "--force" ]]; then
    rm -f ${DIRTY_FILE}
    logger "applying puppet configuration updates..."
    /usr/bin/puppet apply --logdest syslog --onetime --verbose --modulepath "${PUPPET_DIR}/modules" ${PUPPET_DIR}/manifests/site.pp 2>&1 | logger
fi