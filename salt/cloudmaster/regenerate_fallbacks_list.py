#!/usr/bin/env python

import sys

import salt.cli
import salt.client
import salt.key


def collect(prefix):
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
            [k for k, v in d.iteritems()
             if "No such file or directory" in v],
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
    if len(sys.argv) != 2:
        print "Usage: %s <prefix>" % sys.argv[0]
        print "(e.g. %s fp-jp-)" % sys.argv[0]
        sys.exit(1)
    prefix = sys.argv[1]
    json, uninitialized, nonresponding = collect(prefix)
    print json
    if uninitialized:
        print >> sys.stderr, "Uninitialized minions:"
	for name in uninitialized:
            print >> sys.stderr, "   ", name
    if nonresponding:
        print >> sys.stderr, "Non-responding minions:"
        for each in sorted(nonresponding):
            print >> sys.stderr, "   ", each
