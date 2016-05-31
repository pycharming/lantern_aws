#!/usr/bin/env python

from collections import namedtuple
from datetime import datetime, timedelta
import os
import sys

from dateutil.parser import parse as parse_time
import psutil

from misc_util import obj


num_samples = 60 * 24 * 7  # keep last week, assuming 1m precision

path = "/home/lantern/stats"


def save():
    now = datetime.utcnow()
    la1m, _, _ = os.getloadavg()
    net = psutil.net_io_counters(pernic=False)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu = psutil.cpu_times_percent(interval=1)
    duse = psutil.disk_usage('/')
    dtx = psutil.disk_io_counters(perdisk=False)
    if os.path.exists(path):
        lines = file(path).readlines()[-num_samples:]
    else:
        lines = []
    new_line = "|".join(map(str,
        [now, la1m, cpu.user, cpu.system, cpu.iowait, cpu.idle, mem.percent, mem.active, swap.percent, swap.sin + swap.sout,
         duse.percent, dtx.read_bytes + dtx.write_bytes, net.bytes_sent, net.bytes_recv, net.errin + net.errout, net.dropin + net.dropout]))
    print "Time | load avg 1m | user CPU | sys CPU | IO CPU | idle CPU | mem% | active mem | swap% | swap tx | disk% | disk tx | bytes sent | bytes recv | net errors | net drops"
    print new_line
    lines.append(new_line + '\n')
    with file(path + ".tmp", 'w') as f:
        f.writelines(lines)
    os.rename(path + ".tmp", path)

sample = namedtuple('sample', ['time', 'load_avg', 'cpu_user', 'cpu_sys', 'cpu_io', 'cpu_idle', 'mem_pc', 'mem_active', 'swap_pc', 'swap_tx', 'disk_pc', 'disk_tx', 'bytes_sent', 'bytes_recv', 'net_errors', 'net_dropped'])

def parse_line(line):
    time, load_avg, cpu_user, cpu_sys, cpu_io, cpu_idle, mempc, memact, swappc, swaptx, diskpc, disktx, sent, recv, err, drop = line.strip().split('|')
    return sample(parse_time(time), float(load_avg), float(cpu_user), float(cpu_sys), float(cpu_io), float(cpu_idle), float(mempc), int(memact), float(swappc), int(swaptx), float(diskpc), int(disktx), int(sent), int(recv), int(err), int(drop))

def get_bps(minutes_back=None):
    "max(sent, received) bytes per second during the requested interval"
    if minutes_back is None:
        start_time = datetime.fromtimestamp(0)
    else:
        # allow string arguments for command line usage.
        minutes_back = int(minutes_back)
        start_time = datetime.utcnow() - timedelta(minutes=minutes_back)
    rt = obj(seconds=0, bytes_sent=0, bytes_recv=0)
    # Start and end of each run of samples with monotonically increasing
    # bytes_sent and bytes_recv. This is necessary to avoid distortions caused
    # by reboots, downtime, etc.
    start = end = None
    def update():
        rt.seconds += (end.time - start.time).total_seconds()
        assert end.bytes_sent >= start.bytes_sent >= 0, "bad bytes sent! %s..%s (delta %s)" % (start.bytes_sent, end.bytes_sent, end.bytes_sent - start.bytes_sent)
        assert end.bytes_recv >= start.bytes_recv >= 0, "bad bytes recv! %s..%s (delta %s)" % (start.bytes_recv, end.bytes_recv, end.bytes_recv - start.bytes_recv)
        rt.bytes_sent += end.bytes_sent - start.bytes_sent
        rt.bytes_recv += end.bytes_recv - start.bytes_recv
    with file(path) as f:
        while True:
            line = f.readline()
            if not line:
                if start:
                    update()
                break
            s = parse_line(line)
            if s.time < start_time:
                continue
            if not start:
                start = end = s
                continue
            if end.bytes_sent <= s.bytes_sent and end.bytes_recv <= s.bytes_recv:
                end = s
                continue
            update()
            start = end = s
    if not rt.seconds:
        raise RuntimeError('no useful sample intervals')
    ret = max(rt.bytes_sent, rt.bytes_recv) / rt.seconds
    print "Sent %s bytes, received %s bytes in %s seconds (%s bps)" % (rt.bytes_sent, rt.bytes_recv, rt.seconds, ret)
    print ret
    return ret

# XXX: quick check; refactor
def check_load(minutes_back=30):
    print "stats.check_load starting..."
    # command line friendliness
    minutes_back = int(minutes_back)
    start_time = datetime.utcnow() - timedelta(minutes=minutes_back)
    cpu_io = []
    last_swap_tx = None
    swap_tx = 0
    mem_pc = []
    with file(path) as f:
        while True:
            line = f.readline()
            if not line:
                break
            s = parse_line(line)
            if s.time < start_time:
                continue
            if last_swap_tx is None:
                last_swap_tx = s.swap_tx
            delta = s.swap_tx - last_swap_tx
            if delta > 0:
                swap_tx += delta
            last_swap_tx = s.swap_tx
            cpu_io.append(s.cpu_io)
            mem_pc.append(s.mem_pc)
    cpu_io = sum(cpu_io) / len(cpu_io)
    mem_pc = sum(mem_pc) / len(mem_pc)
    if cpu_io > 10 and mem_pc > 80:
        print "overloaded!"
        details = "cpu_io: %.2f, mem_pc: %.2f, swap_tx: %s, num_cores: %s" % (cpu_io, mem_pc, swap_tx, psutil.NUM_CPUS)
        print details
        import alert
        alert.send_to_slack("I think I'm overloaded",
                            details,
                            color="#0000ff",
                            channel="#staging-alerts")
    print "stats.check_load done"

if __name__ == '__main__':
    if len(sys.argv ) < 2:
        print "Usage: %s <command>" % sys.argv[0]
    locals()[sys.argv[1]](*sys.argv[2:])
