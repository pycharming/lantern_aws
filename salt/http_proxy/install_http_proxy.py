#! /usr/bin/env python

import os
import stat
import requests

GH_TOKEN = "{{ pillar['github_token'] }}"
version = "{{ http_proxy_version }}"
url = 'https://api.github.com/repos/getlantern/http-proxy-lantern/releases/tags/' + version
headers = {
    'Authorization': 'token ' + GH_TOKEN,
    'Accept': 'application/vnd.github.v3.raw'
}

print 'Retrieving http-proxy %s...' % version
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
        # We have noticed 'text file busy' errors trying to restart the
        # http-proxy service, which may have to do with the binary being
        # updated while the service is running. According to [1], unlinking the
        # executable before replacing it should fix that.
        #
        # [1] http://stackoverflow.com/questions/1712033/replacing-a-running-executable-in-linux
        if os.path.exists('http-proxy'):
            os.unlink('http-proxy')
        os.rename('http-proxy-temp', 'http-proxy')
        print 'Downloaded ' + download_url
    else:
        r.raise_for_status()
else:
    r.raise_for_status()
