#!/usr/bin/env python

import logging

import psutil


LANTERN_ARGS = set("{{ lantern_args }}".split())

def run():
    any_killed = False
    try:
        lantern_pid = int(file('{{ lantern_pid }}').read().strip())
    except Exception as e:
        logging.exception(e)
        lantern_pid = "<this is not a pid>"
    for proc in psutil.process_iter():
        if (proc.pid == lantern_pid
            or (len(LANTERN_ARGS.intersection(proc.cmdline()))
               > len(LANTERN_ARGS) / 2)):
            logging.info("Terminating %r..." % proc.cmdline())
            proc.terminate()
            any_killed = True
    if not any_killed:
        logging.info("No Lantern found.");


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename='/home/lantern/kill_lantern.log',
                        format='%(asctime)s %(levelname)-8s %(message)s')
    run()
