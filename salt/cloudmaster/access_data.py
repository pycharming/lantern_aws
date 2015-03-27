#!/usr/bin/env python

import salt.cli
import salt.client
import salt.key


prefix = 'fp-'


def collect():
    sk = salt.cli.SaltKey()
    sk.parse_args()
    k = salt.key.Key(sk.config)
    fps = set(s for s in k.list_keys()['minions']
              if s.startswith(prefix))
    c = salt.client.LocalClient()
    d = get_data(c, prefix+'*')
    # Give laggards a second chance
    for name in fps:
        if name not in d:
           d.update(get_data(c, name)) 
    return ("[\n" 
            + ",\n".join(x for x in d.itervalues()
                         if "No such file or directory" not in x)
            + "\n]")

def get_data(client, from_whom):
    return client.cmd(from_whom, "cmd.run", ("cat /home/lantern/access_data.json",))

if __name__ == '__main__':
    print collect()
