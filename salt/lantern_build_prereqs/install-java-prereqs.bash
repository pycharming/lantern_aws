#!/usr/bin/env bash

FILENAME=oab-java.sh

set -e

[ ! -e $FILENAME ] || rm $FILENAME
wget -q https://dqkrsoj09lstx.cloudfront.net/$FILENAME
chmod 700 $FILENAME
./$FILENAME
