import json

import requests
from sleekxmpp import ClientXMPP

lanternctrl_jid = 'linternadoiro@appspot.com/bot'

class OAuth2Bot(ClientXMPP):
    def __init__(self, jid, token):
        ClientXMPP.__init__(self, jid, None, sasl_mech='X-OAUTH2')
        self.credentials['access_token'] = token
        self.add_event_handler("session_start", self.session_start)
    def session_start(self, event):
        self.send_presence()

def read_client_secrets(json_filename):
    d = json.load(file(json_filename))['installed']
    return d['client_id'], d['client_secret']

def get_access_token(client_id, client_secret, refresh_token):
    r = requests.post(
            "https://accounts.google.com/o/oauth2/token",
            verify=True,
            headers={'content-type': 'application/x-www-form-urlencoded'},
            data={'grant_type': 'refresh_token',
                  'refresh_token': refresh_token,
                  'client_id': client_id,
                  'client_secret': client_secret})
    #XXX: handle errors somehow.
    assert r.status_code == 200
    return json.loads(r.content)['access_token']

