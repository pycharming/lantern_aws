#!/usr/bin/env python

import sys

import salt.cli
import salt.client
import salt.key


prefix = 'fp-nl-'


def collect():
    sk = salt.cli.SaltKey()
    sk.parse_args()
    k = salt.key.Key(sk.config)
    fps = set(s for s in k.list_keys()['minions']
              if s.startswith(prefix))
    c = salt.client.LocalClient()
    d = get_data(c, prefix+'*')
    def get_nonresponding():
        return [x for x in fps if x not in d]
    # Give laggards a second chance
    nonresponding = get_nonresponding()
    if nonresponding:
        print >> sys.stderr, ("%s fallback(s) didn't respond at first;"
                              % len(nonresponding))
        print >> sys.stderr, "retrying just once to give them a chance..."
        d.update(get_data(c, nonresponding))
    return (("[\n"
             + ",\n".join(x for x in d.itervalues()
                          if "No such file or directory" not in x)
             + "\n]"),
            get_nonresponding())

def get_data(client, from_whom):
    if isinstance(from_whom, str):
        expr_form = 'glob'
    elif isinstance(from_whom, list):
        expr_form = 'list'
    else:
        assert False, "Unknown from_whom type: %r" % from_whom
    return client.cmd(from_whom,
                      "cmd.run",
                      ("cat /home/lantern/access_data.json",),
                      timeout=20,
                      expr_form=expr_form)

if __name__ == '__main__':
    json, nonresponding = collect()
    print json
    if nonresponding:
        print >> sys.stderr, "Non-responding minions:"
        for each in sorted(nonresponding):
            print >> sys.stderr, "   " + each
