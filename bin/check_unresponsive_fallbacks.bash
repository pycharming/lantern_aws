#!/usr/bin/env bash

HERE=$(dirname $0)

[ -e $HERE/config_overrides.pyc ] && rm $HERE/config_overrides.pyc

SAVE=$([ -e $HERE/config_overrides.py ] && echo "yes")
[ $SAVE ] && echo "Saving config overrides..." && mv $HERE/config_overrides.py $HERE/config_overrides.bak

$HERE/ssh_cloudmaster.py 'sudo salt-run -t 20 manage.down'

[ $SAVE ] && echo "Restoring config overrides..." && mv $HERE/config_overrides.bak $HERE/config_overrides.py
