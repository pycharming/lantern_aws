#!/usr/bin/env python

from datetime import datetime
import os

import psutil


num_samples = 60 * 24 * 7  # keep last week, assuming 1m precision

path = "/home/lantern/stats"


def run():
    now = datetime.utcnow()
    la1m, _, _ = os.getloadavg()
    net = psutil.net_io_counters(pernic=False)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu = psutil.cpu_percent(interval=1)
    if os.path.exists(path):
        lines = file(path).readlines()[-num_samples:]
    else:
        lines = []
    new_line = "|".join(map(str,
        [now, la1m, cpu, mem.percent, mem.active, swap.percent, swap.sin + swap.sout,
         net.bytes_sent, net.bytes_recv, net.errin + net.errout, net.dropin + net.dropout]))
    print "Time | load avg 1m | CPU% | mem% | active mem | swap%% | swaptx | bytes sent | bytes recv | net errors | net drops"
    print new_line
    lines.append(new_line + '\n')
    with file(path + ".tmp", 'w') as f:
        f.writelines(lines)
    os.rename(path + ".tmp", path)


if __name__ == '__main__':
    run()
