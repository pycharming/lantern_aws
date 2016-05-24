#!/usr/bin/env python

import sys
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


if os.path.exists(redis_dump_file):
    retrieve_redis = misc_util.confirm("Do you want to update the Redis file?")

if retrieve_redis:
    print "Retrieving data from Redis..."
    data = redis_shell.zrange('client->bytesInOut', 0, -1, withscores=True)
    with open("dump.csv", "wb") as f:
        writer = csv.writer(f)
        writer.writerows(data)


def clean_data():
    with open("dump.csv", "rb") as f:
        reader = csv.reader(f)
        for device, tx in reader:
            yield float(tx)

rev = reversed([row for row in clean_data()])

try:
    limit_devices = int(sys.argv[1])
except:
    limit_devices = 0
try:
    min_transfer = float(sys.argv[2])
except:
    min_transfer = 0


with_rank = []
total_tx, used_devices, discarded_devices = 0, 0, 0
for tx in rev:
    if tx < min_transfer:
        discarded_devices += 1
        continue
    used_devices += 1
    total_tx += tx
    with_rank += [[used_devices, tx]]

print "Total number of devices:", used_devices

if limit_devices != 0:
    used_devices = min(used_devices, limit_devices)


mean=total_tx / used_devices
median=with_rank[len(with_rank)/2][1]

print "Statistics limited to:", used_devices, "devices with minimum", humanize.naturalsize(min_transfer)
if min_transfer != 0:
    print discarded_devices, "devices transferred less or equal to", humanize.naturalsize(min_transfer)
print "Mean:", humanize.naturalsize(mean)
print "Median:", humanize.naturalsize(median)
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

plt.axhline(y=mean, linewidth=2, color='orange', linestyle='dashed')
plt.text(10, mean, "Mean", fontdict=font)

plt.axhline(y=median, linewidth=2, color='red', linestyle='dashed')
plt.text(10, median, "Median", fontdict=font)

fig = ax.get_figure()
fig.set_size_inches(12, 8)
fig.savefig('device_tx_plot.png')
