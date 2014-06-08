#!/usr/bin/env bash

set -e

LOG=$(dirname $0)/install-go.log
FILENAME=go1.3rc1.linux-amd64.tar.gz
SHA1_CHECKSUM=affaccfd69a694e0aa59466450e4db5260aeb1a3

wget -qct 3 http://golang.org/dl/$FILENAME >> $LOG 2>&1
echo "$SHA1_CHECKSUM *$FILENAME" | sha1sum -c - >> $LOG 2>&1
tar -C /usr/local -zxf $FILENAME >> $LOG 2>&1
rm $FILENAME >> $LOG 2>&1

