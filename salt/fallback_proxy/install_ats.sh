#! /usr/bin/env sh

PREFIX=/opt/ts
PLUGIN_DIR=$PREFIX/libexec/trafficserver
CONFIG_DIR=$PREFIX/etc/trafficserver
SRC_DIR=/home/lantern

PLUGIN_FILE=$SRC_DIR/lantern-auth.so
RECORDS_FILE=$SRC_DIR/records.config
CERT_FILE=$SRC_DIR/key.pem
CERT_PASS="Be Your Own Lantern"
AUTH_TOKEN=`cat /home/lantern/auth_token.txt`

echo 'Installing package...'
mkdir -p $PREFIX
curl -L https://s3.amazonaws.com/lantern-aws/apache-traffic-server-5.3.1-ubuntu-14-64bit.tar.gz | tar zxC $PREFIX
cp $PREFIX/bin/trafficserver /etc/init.d/
echo 'Copying plugin and cert...'
echo 'Changing configuration...'
echo "$PLUGIN_DIR/lantern-auth.so $AUTH_TOKEN" > $CONFIG_DIR/plugin.config
cp $CERT_FILE $CONFIG_DIR/
echo "dest_ip=* ssl_cert_name=key.pem ssl_key_dialog=\"exec:/bin/echo $CERT_PASS\"" > $CONFIG_DIR/ssl_multicert.config
