#!/usr/bin/env bash

wget -q https://d3g17h6tzzjzlu.cloudfront.net/apache-maven-3.0.5-bin.tar.gz
tar zxf apache-maven-3.0.5-bin.tar.gz
rm apache-maven-3.0.5-bin.tar.gz
mv apache-maven-3.0.5 /usr/local/
echo 'export PATH=/usr/local/apache-maven-3.0.5/bin:$PATH' >> /etc/profile

