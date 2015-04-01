#!/usr/bin/env python

{% from 'ip.sls' import external_ip %}

import os
from random import SystemRandom
random = SystemRandom()


all_words = file('/usr/share/dict/words').read().split()

random_word = lambda: random.choice(all_words)

def random_words(*dist):
    return ' '.join(random_word().capitalize().replace("'s", "")
                    for _ in xrange(weighted_choice(*dist)))

def weighted_choice(*dist):
    "For quick&dirtiness, weights must be integers."
    return random.choice(sum(([item] * weight for item, weight in dist), []))

def gen_cert_call():

    "Typical-ish parameters with some very unscientific randomization."

    args = {}
    args['keyalg'] = weighted_choice(('RSA', 4), ('EC', 1))

    # `man keytool`
    default_keysize = {'RSA': 2048, 'DSA': 1024, 'EC': 256}[args['keyalg']]

    args['keysize'] = weighted_choice((default_keysize, 5),
                                      (default_keysize * 2, 1))

    common_name = "CN=%s" % random_words((1, 5), (2, 10), (3, 2), (4, 1))

    if random.randint(0, 5) == 0:
        org = ""
    else:
        org = "O=%s" % random_words((1, 5), (2, 10), (3, 2), (4, 1))

    # Omit Organizational Unit more often than not.
    if org and random.randint(0,3) == 0:
        org_unit = "OU=%s" % random_words((1, 10), (2, 5), (3, 2), (4, 1))
    else:
        org_unit = ""

    # If we provide OU we are on the verbose side, so let's not omit locality.
    if not org_unit and random.randint(0, 5) == 0:
        loc = state = country = ""
    else:
        #XXX: Get a database of localities?
        loc = "L=%s" % random_words((1, 5), (2, 1))

        # http://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_population
        #
        # Weight by tens of millions of inhabitants, round to nearest, add 3 to CA
        # and 2 to NY for being tech hotspots.  Cut off at Massachusets to get Microsoft,
        # MIT, and Harvard in.  Otherwise, forgive my ignorance.  -- aranhoide
        state = "S=%s" % weighted_choice(('California', 7),
                                         ('Texas', 3),
                                         ('New York', 4),
                                         ('Florida', 2),
                                         ('Illinois', 1),
                                         ('Pennsylvania', 1),
                                         ('Ohio', 1),
                                         ('Georgia', 1),
                                         ('Michigan', 1),
                                         ('North Carolina', 1),
                                         ('New Jersey', 1),
                                         ('Virginia', 1),
                                         ('Washington', 1),
                                         ('Massachusets', 1))

        # XXX: get database of 'states' for other countries.
        country = "C=US"
    args['dname'] = repr(', '.join(filter(None, [common_name,
                                                 org_unit,
                                                 org,
                                                 loc,
                                                 state,
                                                 country])))

    # Randomize cert validity date up to three months ago.
    months_back = random.randint(0,3)
    days_back = random.randint(0,30)
    args['startdate'] = "-%sm-%sd" % (months_back, days_back)

    args['validity'] = weighted_choice((365, 8), (365*2, 4), (365*3, 1))

    argstr = " ".join("-%s %s" % (key, val) for key, val in args.iteritems())
    # DRY: org.lantern.proxy.CertTrackingSslEngineSource in the client.
    return "keytool -genkeypair -alias fallback -keypass 'Be Your Own Lantern' -storepass 'Be Your Own Lantern' -keystore /home/lantern/littleproxy_keystore.jks -ext san=ip:{{ external_ip(grains) }} " + argstr


if __name__ == '__main__':
    os.system(gen_cert_call())

