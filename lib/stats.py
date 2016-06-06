#!/usr/bin/env python

"""
Maintain, and help read and digest, a rolling log of recent system resource
usage.
"""

from __future__ import division

from collections import namedtuple
from datetime import datetime, timedelta
import os
import sys

from dateutil.parser import parse as parse_time
import psutil

from misc_util import obj


__all__ = ['save', 'summary', 'get_bps']


num_samples = 60 * 24 * 7  # keep last week, assuming 1m precision

stats_path = "/home/lantern/stats"

# There are two major classes of stats handled here: cumulative ones that are
# defined as a counter since last reboot, and independent instant samples. For
# the former we accumulate by adding deltas (with some care to handle reboots,
# which reset the stat). For the latter we average over the requested period.

delta_val = namedtuple('accum_val', ['val', 'prev'])
avg_val = namedtuple('avg_val', ['val', 'nsamples'])

delta_0 = delta_val(val=None, prev=None)

avg_0 = avg_val(val=None, nsamples=0)

def delta_reduce_step(accum, newval):
    if accum.val is None:
        return delta_val(0, newval)
    nextval = accum.val + newval
    # If the new value is lower than the accumulated one, there has been a
    # reboot, in which case we want to use the absolute value in the sample
    # instead of the delta from the previous sample.
    if newval >= accum.prev:
        nextval -= accum.prev
    return delta_val(nextval, newval)

def avg_reduce_step(accum, newval):
    return avg_val(val=((accum.val or 0) * accum.nsamples + newval)
                       / (accum.nsamples + 1),
                   nsamples=accum.nsamples + 1)

accum_type = namedtuple('accum_type', ['init', 'step_fn'])

delta_type = accum_type(delta_0, delta_reduce_step)
avg_type = accum_type(avg_0, avg_reduce_step)
stat_def = namedtuple('stat_def', ['name', 'display_name', 'accum_type', 'parser'])
# DRY: this must be kept consistent with save(); AFAICT the rest of this module
# derives its data model from here.
stat_defs = [stat_def(*args) for args in [
    ('time', 'time', None, parse_time),
    ('load_avg', 'load avg 1m', avg_type, float),
    ('cpu_user', 'user CPU %', avg_type, float),
    ('cpu_sys', 'sys CPU %', avg_type, float),
    ('cpu_io', 'I/O CPU %', avg_type, float),
    ('cpu_idle', 'idle CPU %', avg_type, float),
    ('mem_pc', 'mem %', avg_type, float),
    ('mem_active', 'active mem', avg_type, int),
    ('swap_pc', 'swap %', avg_type, float),
    ('swap_tx', 'swap TX', delta_type, int),
    ('disk_pc', 'disk %', avg_type, float),
    ('disk_tx', 'disk TX', delta_type, int),
    ('bytes_sent', 'bytes sent', delta_type, int),
    ('bytes_recv', 'bytes recv', delta_type, int),
    ('net_errors', 'net errors', delta_type, int),
    ('net_dropped', 'net dropped', delta_type, int)]]

name2def = {d.name: d for d in stat_defs}

sample = namedtuple('sample', [d.name for d in stat_defs])

def save():
    """
    Append a serialized `sample` to the rolling log.
    """
    now = datetime.utcnow()
    la1m, _, _ = os.getloadavg()
    net = psutil.net_io_counters(pernic=False)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu = psutil.cpu_times_percent(interval=1)
    duse = psutil.disk_usage('/')
    dtx = psutil.disk_io_counters(perdisk=False)
    if os.path.exists(stats_path):
        # Remove old samples to keep the size of the log bounded.
        lines = file(stats_path).readlines()[-num_samples:]
    else:
        lines = []
    # DRY: stat_defs
    new_line = "|".join(map(str,
        [now, la1m, cpu.user, cpu.system, cpu.iowait, cpu.idle, mem.percent, mem.active, swap.percent, swap.sin + swap.sout,
         duse.percent, dtx.read_bytes + dtx.write_bytes, net.bytes_sent, net.bytes_recv, net.errin + net.errout, net.dropin + net.dropout]))
    print " | ".join(d.display_name for d in stat_defs)
    print new_line
    lines.append(new_line + '\n')
    with file(stats_path + ".tmp", 'w') as f:
        f.writelines(lines)
    os.rename(stats_path + ".tmp", stats_path)

def parse_line(line):
    return sample(*(d.parser(s) for d, s in zip(stat_defs, line.strip().split('|'))))

def get_stats(fileobj, start_time):
    while True:
        line = fileobj.readline()
        if not line:
            break
        s = parse_line(line)
        if s.time < start_time:
            continue
        yield s

def reduce_stats(dimensions, samples):
    actual_start_time = None
    defs = map(name2def.get, dimensions)
    accum_vals, accum_fns = zip(*(d.accum_type for d in defs))
    for s in samples:
        if actual_start_time is None:
            actual_start_time = s.time
        new_vals = [getattr(s, dim) for dim in dimensions]
        accum_vals = [fn(accum, new)
                      for fn, accum, new in zip(accum_fns, accum_vals, new_vals)]
    return {'actual_start_time': actual_start_time,
            'values': {dim: val
                       for dim, (val, _) in zip(dimensions, accum_vals)}}

def summary(dimensions, minutes_back=None):
    """
    Return a summary of each of the requested dimensions across the samples.

    Examples of dimensions are 'cpu_io' or 'disk_tx'.

    A summary can be either

      - an average, useful for stats that are independent point-in-time
        samples (i.e., dimensions with accum_type==avg_type), or

      - a total quantity representing the accrued value over the samples,
        useful for dimensions that increase monotonically (with the exception
        of being reset in reboots).  These are dimensions with
        accum_type==delta_type.
    """
    if minutes_back is None:
        start_time = datetime.fromtimestamp(0)
    else:
        # allow string arguments for command line usage.
        minutes_back = int(minutes_back)
        start_time = datetime.utcnow() - timedelta(minutes=minutes_back)
    with file(stats_path) as f:
        return reduce_stats(dimensions, get_stats(f, start_time))


def get_bps(minutes_back=None):
    """
    Estimate recent network transfer of this proxy.

    If `minutes_back` is provided, samples older than that are ignored. Even if
    no limit is provided, this module keeps a limited amount of history (as of
    this writing, up to one week).
    """
    s = summary(['bytes_sent', 'bytes_recv'], minutes_back)
    sent = s['values']['bytes_sent']
    recv = s['values']['bytes_recv']
    seconds = (datetime.utcnow() - s['actual_start_time']).total_seconds()
    ret = max(sent, recv) / seconds
    print "Sent %s bytes, received %s bytes in %s seconds (%s bps)" % (sent, recv, seconds, ret)
    print ret
    return ret

# XXX: quick check; move to check_load when stats.py becomes a library.
def check_load(minutes_back=30):
    s = summary(['cpu_io', 'mem_pc', 'swap_tx'], minutes_back=minutes_back)
    mem_pc = s['values']['mem_pc']
    cpu_io = s['values']['cpu_io']
    swap_tx = s['values']['swap_tx']
    details = "cpu_io: %.2f, mem_pc: %.2f, swap_tx: %s, num_cores: %s" % (cpu_io, mem_pc, swap_tx, psutil.NUM_CPUS)
    print details
    if cpu_io > 3 and mem_pc > 85:
        print "overloaded!"
        import alert
        alert.send_to_slack("I think I'm overloaded",
                            details,
                            color="#0000ff",
                            channel="#staging-alerts")

if __name__ == '__main__':
    if len(sys.argv ) < 2:
        print "Usage: %s <command>" % sys.argv[0]
    locals()[sys.argv[1]](*sys.argv[2:])
