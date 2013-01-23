#!/usr/bin/env python

# This needs the Google OAuth2 client library for Python, which you can
# download at
# code.google.com/p/google-api-python-client/downloads/detail?name=oauth2client-1.0.tar.gz

import sys

from oauth2client.client import flow_from_clientsecrets


try:
    client_secrets_filename = sys.argv[1]
except IndexError:
    print "Usage: %s <client secrets file>" % sys.argv[0]
    sys.exit(1)

flow = flow_from_clientsecrets(client_secrets_filename,
                               scope='https://www.googleapis.com/auth/googletalk',
                               redirect_uri='urn:ietf:wg:oauth:2.0:oob')

print "Go to", flow.step1_get_authorize_url(), "and give me the code you get"

code = raw_input()

credentials = flow.step2_exchange(code)

print "Access token is", credentials.access_token
print "Refresh token is", credentials.refresh_token
