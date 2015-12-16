#! /usr/bin/env python

import os
import stat
import requests

GH_TOKEN = "{{ pillar['github_token'] }}"
VERSION = 'v0.0.5'

url = 'https://api.github.com/repos/getlantern/http-proxy-lantern/releases/tags/' + VERSION
headers = {
    'Authorization': 'token ' + GH_TOKEN,
    'Accept': 'application/vnd.github.v3.raw'
}
print 'Retrieving http-proxy %s...' % VERSION
r = requests.get(url, headers=headers)
if(r.ok):
    release = r.json()
    asset = release['assets'][0]
    download_url = asset['url']
    headers['Accept'] = 'application/octet-stream'
    r = requests.get(download_url, headers=headers, stream=True)
    if(r.ok):
        with open('http-proxy-temp', 'wb') as f:
            for chunk in r.iter_content(chunk_size=1048576):
                if chunk:
                    f.write(chunk)
        os.chmod('http-proxy-temp', stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        # We have noticed some errors, which may have to do with the binary
        # being updated while the service is running.
        os.system('sudo service http-proxy stop')
        os.rename('http-proxy-temp', 'http-proxy')
        # We don't (re)start the service again here because it has other
        # dependencies; the salt configuration will take care of that.
        print 'Downloaded ' + download_url
    else:
        r.raise_for_status()
else:
    r.raise_for_status()
