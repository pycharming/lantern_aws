#!/usr/bin/env bash

FILENAME=install4j_linux_5_1_3.deb
wget -q https://d3g17h6tzzjzlu.cloudfront.net/$FILENAME
dpkg -i $FILENAME
rm $FILENAME
