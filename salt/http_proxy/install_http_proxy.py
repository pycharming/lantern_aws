#! /usr/bin/env python

import os
import stat
import requests
import json

GH_TOKEN = "{{ pillar['github_token'] }}"
url = 'https://api.github.com/repos/getlantern/http-proxy-lantern/releases/latest'

headers = {
    'Authorization': 'token ' + GH_TOKEN,
    'Accept': 'application/vnd.github.v3.raw'
}

print 'Retrieving latest binary from http-proxy-lantern repo...'
r = requests.get(url, headers=headers)
if(r.ok):
    release = json.loads(r.text or r.content)
    asset = release['assets'][0]
    download_url = asset['url']
    headers['Accept'] = 'application/octet-stream'
    r = requests.get(download_url, headers=headers, stream=True)
    if(r.ok):
        with open('http-proxy-temp', 'wb') as f:
            for chunk in r.iter_content(chunk_size=1048576):
                if chunk:
                    f.write(chunk)
        os.rename('http-proxy-temp', 'http-proxy')
        os.chmod('http-proxy', stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        print 'Downloaded ' + download_url
    else:
        r.raise_for_status()
else:
    r.raise_for_status()
