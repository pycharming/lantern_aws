#!/usr/bin/env bash

# This updates the certs so I can make TLS connections to S3.
sudo apt-get update && sudo apt-get upgrade -y

wget -q https://s3.amazonaws.com/lantern/latest-64.deb
dpkg -i latest-64.deb
rm latest-64.deb
