#!/usr/bin/env python

import logging

import librato
import psutil


SOURCE = "proxy-{{ pillar['instance_id'] }}"
# XXX: move these into a pillar if/when we make this secret.
LIBRATO_USERNAME = 'ox@getlantern.org'
LIBRATO_TOKEN =   "7c10ebf9e817e301cc578141658284bfa9f4a15bf938143b386142f854be0afe"


def run():
    try:
        parent_proc = psutil.Process(
                int(file("{{ lantern_pid }}").read().strip()))
        java_proc, = parent_proc.get_children()
        meminfo = java_proc.get_ext_memory_info()
        process_memory = meminfo.rss - meminfo.shared
    except (IOError, ValueError, psutil.NoSuchProcess):
        logging.warn("Lantern not running; reporting zero stats.")
        process_memory = 0
    conn = librato.connect(LIBRATO_USERNAME, LIBRATO_TOKEN)
    q = conn.new_queue()
    q.add("process_memory", process_memory, source=SOURCE)
    q.submit()


if __name__ == '__main__':
    # Use WARN level because librato is so chatty.
    logging.basicConfig(level=logging.WARN,
                        filename='/home/lantern/report_stats.log',
                        format='%(asctime)s %(levelname)-8s %(message)s')
    try:
        run()
    except Exception, e:
        logging.exception(e)
