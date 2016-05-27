#!/usr/bin/env python

import sys
import getopt
import os
import pandas as pd
import matplotlib
import csv

matplotlib.use('Agg')

import humanize
import matplotlib.pyplot as plt
import numpy as np
import misc_util

from redis_util import redis_shell

redis_dump_file = "dump.csv"

def clean_data():
    with open(redis_dump_file, "rb") as f:
        reader = csv.reader(f)
        for device, tx in reader:
            yield float(tx)

def usage():
    print "Usage:"
    print "device_tx_analysis.py [--limitdevices=<n>|-d=<n>] [--mintransfer=<n>|-t=<n>] [--output=<path>|-o=<path>]"

def main():
    limit_devices = 0
    min_transfer = 0
    output = 'device_tx_plot.png'

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hdto", ["help", "limitdevices=", "mintransfer=", "output="])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-d", "--limitdevices"):
            limit_devices = int(a)
        elif o in ("-t", "--mintransfer"):
            min_transfer = int(a)
        elif o in ("-o", "--output"):
            output = a
        else:
            assert False, "unhandled option"

    retrieve_redis = True
    if os.path.exists(redis_dump_file):
        retrieve_redis = misc_util.confirm("Do you want to update the Redis file?")

    if retrieve_redis:
        print "Retrieving data from Redis..."
        data = redis_shell.zrange('client->bytesInOut', 0, -1, withscores=True)
        with open("dump.csv", "wb") as f:
            writer = csv.writer(f)
            writer.writerows(data)

    rev = reversed([r for r in clean_data()])

    with_rank = []
    total_tx, used_devices, discarded_devices = 0, 0, 0
    for tx in rev:
        if tx < min_transfer:
            discarded_devices += 1
            continue
        used_devices += 1
        total_tx += tx
        with_rank.append([used_devices, tx])

    print "Total number of devices:", used_devices

    if limit_devices != 0:
        used_devices = min(used_devices, limit_devices)

    mean=total_tx / used_devices
    median=with_rank[len(with_rank)/2][1]
    percentile90=with_rank[int(0.1*used_devices)][1]
    percentile95=with_rank[int(0.05*used_devices)][1]

    print "Statistics limited to:", used_devices, "devices with minimum", humanize.naturalsize(min_transfer)
    if min_transfer != 0:
        print discarded_devices, "devices transferred less or equal to", humanize.naturalsize(min_transfer)
    print "Mean:", humanize.naturalsize(mean)
    print "Median:", humanize.naturalsize(median)
    print "95 percentile:", humanize.naturalsize(percentile95)
    print "90 percentile:", humanize.naturalsize(percentile90)
    print "Max transfer by a single device:", humanize.naturalsize(with_rank[0][1])
    print "Min transfer by a single device (in sample):", humanize.naturalsize(with_rank[len(with_rank)-1][1])

    print "Generating plot..."

    df = pd.DataFrame(with_rank)
    df.columns = ['Rank', 'Mb/device']

    ax = df.plot(logy=True, kind='line',x='Rank',y='Mb/device')

    font = {'family': 'Arial',
            'color':  'black',
            'weight': 'normal',
            'size': 16,
    }

    plt.text(0.98, 0.88,
             str(used_devices) + " devices with min " + humanize.naturalsize(min_transfer),
             fontdict=font,
             horizontalalignment='right',
             verticalalignment='center',
             transform=ax.transAxes)

    plt.text(0.98, 0.84,
             str(discarded_devices) + " devices discarded",
             fontdict=font,
             horizontalalignment='right',
             verticalalignment='center',
             transform=ax.transAxes)

    font = {'family': 'Arial',
            'color':  'grey',
            'weight': 'normal',
            'size': 16,
    }

    plt.axhline(y=mean, linewidth=2, color='#FF9100', linestyle='dashed')
    plt.text(10, mean, "Mean " + humanize.naturalsize(mean), fontdict=font)

    plt.axhline(y=median, linewidth=2, color='red', linestyle='dashed')
    plt.text(10, median, "Median " + humanize.naturalsize(median), fontdict=font)

    plt.axhline(y=percentile95, linewidth=2, color='#ffb300', linestyle='dashed')
    plt.text(10, percentile95, "95 percentile " + humanize.naturalsize(percentile95), fontdict=font)

    fig = ax.get_figure()
    fig.set_size_inches(12, 8)
    fig.savefig(output)


if __name__ == "__main__":
    main()
