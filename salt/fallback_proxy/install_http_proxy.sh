#! /usr/bin/env sh

echo 'Installing http proxy ...'
rm -f http-proxy.tmp
curl -L https://github.com/getlantern/http-proxy/releases/download/v0.0.1-mobile/http-proxy -o http-proxy.tmp
chmod u+x http-proxy.tmp
mv -f http-proxy.tmp http-proxy
echo 'Done'
