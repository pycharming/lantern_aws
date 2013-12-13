#!/usr/bin/env bash

VERSION=3.1.1
wget -q https://dqkrsoj09lstx.cloudfront.net/apache-maven-${VERSION}-bin.tar.gz
tar zxf apache-maven-${VERSION}-bin.tar.gz
rm apache-maven-${VERSION}-bin.tar.gz
mv apache-maven-${VERSION} /usr/local/
echo "export PATH=/usr/local/apache-maven-${VERSION}/bin:\$PATH" >> /etc/profile
hash -r
