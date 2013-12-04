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
        connections = len(java_proc.get_connections(kind='inet'))
        io = java_proc.get_io_counters()
        io_ops = io.read_count + io.write_count
        io_bytes = io.read_bytes + io.write_bytes
    except (IOError, ValueError, psutil.NoSuchProcess):
        logging.warn("Lantern not running; reporting zero stats.")
        process_memory = connections = io_ops = io_bytes = 0
    net = psutil.net_io_counters()
    conn = librato.connect(LIBRATO_USERNAME, LIBRATO_TOKEN)
    q = conn.new_queue()
    for k, v in [('process_memory', process_memory),
                 ('process_connections', connections),
                 ('process_io_ops', io_ops),
                 ('process_io_bytes', io_bytes),
                 ('bytes_sent', net.bytes_sent),
                 ('bytes_received', net.bytes_recv),
                 ('net_errors', net.errin + net.errout),
                 ('net_drops', net.dropin + net.dropout)]:
        q.add(k, v, source=SOURCE)
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
