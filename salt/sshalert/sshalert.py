#!/usr/bin/env python

import sys

try:

    import os

    import alert
    import misc_util
    try:
        from redis_util import redis_shell
    except ImportError:
        # sshalert is enabled on all vpss, some of which don't have redis_shell.
        redis_shell = None

    ip = os.environ['SSH_CONNECTION'].split(' ')[0]
    user = os.environ['USER']

    try:
        whitelisted = redis_shell is not None and redis_shell.exists('sshalert-whitelist:%s' % ip)
    except Exception,e:
        print >> sys.stderr, "Unable to check whitelisted status, assuming whitelisted: "
        traceback.print_exc(file=sys.stderr)
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
    sys.exit(0)
