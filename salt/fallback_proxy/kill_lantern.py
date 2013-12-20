#!/usr/bin/env python

import logging

import psutil


LANTERN_ARGS = set(['java', '-Djna.nosys=true', '-jar', '--disable-ui',
    '--force-give', '--oauth2-client-secrets-file',
    '--oauth2-user-credentials-file', '--server-port',
    '--server-protocol', '--auth-token-file', '--as-fallback-proxy',
    '--keystore', '--controller-id', '--instance-id', '--report-ip'])


def run():
    any_killed = False
    for proc in psutil.process_iter():
        if (len(LANTERN_ARGS.intersection(proc.cmdline))
            > len(LANTERN_ARGS) / 2):
            logging.info("Terminating %r..." % proc.cmdline)
	    proc.terminate()
            any_killed = True
    if not any_killed:
        logging.info("No Lantern found.");


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename='/home/lantern/kill_lantern.log',
                        format='%(asctime)s %(levelname)-8s %(message)s')
    run()
