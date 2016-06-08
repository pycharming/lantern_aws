#!/usr/bin/env python

import sys
import traceback

try:

    import os
    import requests

    import alert
    import misc_util

    ip = os.environ['SSH_CONNECTION'].split(' ')[0]
    user = os.environ['USER']

    try:
        resp = requests.get('https://ops.lantern.io/is-ip-whitelisted',
                            params={'ip': ip},
                            headers={'ssh-whitelist-query-token': os.environ['SSH_WHITELIST_QUERY_TOKEN']})
        if resp.ok:
            whitelisted = resp.text == 'yes'
        else:
            print >> sys.stderr, 'Unable to check whitelisted status: server replied %s %s' % (resp.status_code, resp.text)
            print >> sys.stderr, 'Assuming whitelisted'
            whitelisted = True
    except Exception, e:
        print >> sys.stderr, "Unable to check whitelisted status, assuming whitelisted: ", e
        whitelisted = True

    original_cmd = os.getenv('SSH_ORIGINAL_COMMAND')

    if not whitelisted:
        # WARNING: if you make any changes to this check or its response you better
        # test them in a more disposable machine (e.g., a test proxy, rather than a
        # test cloudmaster).  You can easily lock yourself out of the test machine.
        # Keeping a backup of this file and a separate SSH session open while you
        # test this should help prevent such lockout.
        if not original_cmd:
            print >> sys.stderr, "Your IP is not whitelisted.  Please use lantern_aws/bin/hussh instead."
            print >> sys.stderr, "If you continue, ssh-alert noise will ensue.  You'll need to warn the"
            print >> sys.stderr, "team about this, or somebody will have to manually check whether this"
            print >> sys.stderr, "was a legit login."
            force = misc_util.confirm("Continue anyway?")
        else:
            if original_cmd.split()[0] == '_force_':
                force = True
                original_cmd = original_cmd[len('_force_'):].lstrip()
            else:
                print >> sys.stderr, "Your IP is not whitelisted.  Please use lantern_aws/bin/hussh instead."
                print >> sys.stderr, "If that's not possible, use _force_, e.g.:"
                print >> sys.stderr, '\n   ssh <my-address> "_force_ %s"\n' % original_cmd
                force = False
        if force:
            print >> sys.stderr, "Please leave a note about this login in #ssh-alerts (preferrably)"
            print >> sys.stderr, "or in the dev mailing list."
        else:
            sys.exit(1)
        alert.send_to_slack("SSH login",
                            "User %s *logging in* from IP %s" % (user, ip),
                            channel="#ssh-alerts")

    if original_cmd:
        ret = os.system(original_cmd)
    else:
        ret = os.system(os.environ['SHELL'])

    if not whitelisted:
        alert.send_to_slack("SSH logout",
                            "User %s from IP %s logging out" % (user, ip),
                            color="good",
                            channel="#ssh-alerts")

    sys.exit(ret)

except SystemExit:
    raise

except:
    print >> sys.stderr, "Uncaught exception trying to check for SSH whitelisting:"
    traceback.print_exc(sys.stderr)
    print >> sys.stderr, "Assuming whitelisted."
    sys.exit(0)
