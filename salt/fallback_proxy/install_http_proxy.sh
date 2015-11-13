#! /usr/bin/env sh

VERSION=v0.0.2
echo "Installing http proxy $VERSION..."
rm -f http-proxy.tmp
curl -L https://github.com/getlantern/http-proxy/releases/download/$VERSION/http-proxy -o http-proxy.tmp
chmod u+x http-proxy.tmp
mv -f http-proxy.tmp http-proxy
echo 'Done'
