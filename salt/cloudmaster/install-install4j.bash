#!/usr/bin/env bash

FILENAME=install4j_linux_5_1_3.deb
wget -q https://dqkrsoj09lstx.cloudfront.net/$FILENAME
dpkg -i $FILENAME
rm $FILENAME
