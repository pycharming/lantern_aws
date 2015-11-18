#!/usr/bin/env sh

KEYSTORE=/home/lantern/littleproxy_keystore.jks
CERT_PASS="Be Your Own Lantern"
CERT_FILE=/opt/ts/etc/trafficserver/key.pem
keytool -v -importkeystore -srckeystore $KEYSTORE -srcalias fallback --srcstorepass "$CERT_PASS" -destkeystore /tmp/keystore.p12 -deststoretype PKCS12 --deststorepass "$CERT_PASS"
openssl pkcs12 -in /tmp/keystore.p12 -passin pass:"$CERT_PASS" -out $CERT_FILE -passout pass:"$CERT_PASS" # key.pem will be used by ATS
rm /tmp/keystore.p12
