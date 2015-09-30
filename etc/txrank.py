#!/usr/bin/env python

import sys

try:
    from influxdb import InfluxDBClient
except ImportError:
    print "You need the python-influxdb package installed.  Try:"
    print "   pip install influxdb"
    sys.exit(1)


def name_by_ip():
    import vultr_util
    import do_util
    ret = {}
    for x in vultr_util.vultr.server_list(None).values():
        ret[x['main_ip']] = x['label']
    for x in do_util.do.get_all_droplets():
        ret[x.ip_address] = x.name
    return ret

def queued_names():
    from redis_util import redis_shell
    nbyip = name_by_ip()
    return set(nbyip.get(cfg.split('|')[0])
               for dc in ['doams3', 'vltok1']
               for cfg in redis_shell.lrange('%s:srvq' % dc, 0, -1))

def collect_pairs():
    query = "SELECT DERIVATIVE(last(value)) AS bytes FROM \"collectd\".\"default\".\"interface_rx\" WHERE type='if_octets' AND instance='eth0' AND time > now() - 1d GROUP BY time(1h), host FILL(none)"
    client = InfluxDBClient('influx.getlantern.org', 8080, 'test', 'test', 'collectd', True)
    result = client.query(query)
    return list(sorted((sum(x['bytes'] for x in item[1]), item[0][1]['host'])
                       for item in result.items()))

if __name__ == '__main__':
    def usage():
        print "Usage:"
        print "    %s [<lines, default 10>]" % sys.argv[0]
        print
        print "Enter a negative number to get the VPSs with highest traffic instead."
        print
        print "Servers which are still queued (and thus not used yet) are not printed"
        print "by default.  Add the --queued flag if you want to print them"
        sys.exit(1)
    args = sys.argv[1:]
    try:
        args.remove('--queued')
        queued = True
    except ValueError:
        queued = False
    if len(args) == 0:
        lines = 10
    elif len(args) == 1:
        try:
            lines = int(args[0])
        except ValueError:
            usage()
    else:
        usage()
    print "Collecting influx data..."
    pairs = collect_pairs()
    if not queued:
        print "Collecting queued names (this will take a while)..."
        qn = queued_names()
        pairs = [x for x in pairs if x[1] not in qn]
    if lines > 0:
        pairs = pairs[:lines]
        units = "MB"
        divisor = 1024 * 1024
    else:
        pairs = pairs[lines:]
        units = "GB"
        divisor = 1024 * 1024 * 1024
    print
    print "%-20s%15s" % ("Name", "Transfer (%s)" % units)
    print "=" * 35
    for tx, name in pairs:
        print "%-20s%15.3f" % (name, tx / divisor)

