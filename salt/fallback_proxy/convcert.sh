#!/usr/bin/env sh

KEYSTORE=/home/lantern/littleproxy_keystore.jks
CERT_PASS="Be Your Own Lantern"
KEY_FILE=/home/lantern/key.pem
CERT_FILE=/home/lantern/cert.pem
keytool -v -importkeystore -srckeystore $KEYSTORE -srcalias fallback --srcstorepass "$CERT_PASS" -destkeystore /tmp/keystore.p12 -deststoretype PKCS12 --deststorepass "$CERT_PASS"
openssl pkcs12 -in /tmp/keystore.p12 -passin pass:"$CERT_PASS" -out $KEY_FILE -passout pass:"$CERT_PASS" -nocerts -nodes
openssl pkcs12 -in /tmp/keystore.p12 -passin pass:"$CERT_PASS" -out /tmp/cert.pem -passout pass:"$CERT_PASS" -clcerts -nokeys
openssl x509 -in /tmp/cert.pem -out $CERT_FILE
rm /tmp/keystore.p12 /tmp/cert.pem
