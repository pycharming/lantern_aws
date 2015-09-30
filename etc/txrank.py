#!/usr/bin/env python

import sys

try:
    from influxdb import InfluxDBClient
except ImportError:
    print "You need the python-influxdb package installed.  Try:"
    print "   pip install influxdb"
    sys.exit(1)

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
        print "(Enter a negative number to get the VPSs with highest traffic instead.)"
        sys.exit(1)
    if len(sys.argv) == 1:
        lines = 10
    elif len(sys.argv) == 2:
        try:
            lines = int(sys.argv[1])
        except ValueError:
            usage()
    else:
        usage()
    pairs = collect_pairs()
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

