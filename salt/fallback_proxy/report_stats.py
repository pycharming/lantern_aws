#!/usr/bin/env python

import logging
import subprocess

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
                 ('net_drops', net.dropin + net.dropout),
                 ('page_outs', get_swapouts())]:
        q.add(k, v, source=SOURCE)
    q.submit()

# vmstat will generate a report like:
#
#procs -----------memory---------- ---swap-- -----io---- -system-- ----cpu----
# r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa
# 3  0      0 4693220 200008 1207540    0    0    15    25  381  553 34  6 61  0
# 1  0      0 4690560 200016 1207380    0    0     0    32  962 1406 26  1 73  0
#
# The next-to-last line is an average since system startup.  We are interested
# in the last one, which are the results in our sampling period.
def get_swapouts():
    lines = [line.split()
             for line in subprocess.check_output(["vmstat", "10", "2"]).split("\n")
             # The report is \n terminated; drop the latest blank line.
             if line.strip()]
    so_index = lines[1].index("so")
    return int(lines[-1][so_index])

if __name__ == '__main__':
    # Use WARN level because librato is so chatty.
    logging.basicConfig(level=logging.WARN,
                        filename='/home/lantern/report_stats.log',
                        format='%(asctime)s %(levelname)-8s %(message)s')
    try:
        run()
    except Exception, e:
        logging.exception(e)
