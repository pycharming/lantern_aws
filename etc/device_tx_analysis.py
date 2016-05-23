#!/usr/bin/env python

import sys
import os
import pandas as pd
import matplotlib
import csv

matplotlib.use('Agg')

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
            yield float(tx) / 1024.0 / 1024.0

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
total_tx, num_devices = 0, 0
for tx in rev:
    if tx < min_transfer:
        continue
    num_devices += 1
    total_tx += tx
    with_rank += [[num_devices, tx]]

print "Total number of devices:", num_devices

if limit_devices != 0:
    num_devices = min(num_devices, limit_devices)


print "Statistics limited to:", num_devices, "devices with minimum", min_transfer, "Mb"
print "Average:", total_tx / num_devices, "Mb/device"
print "Median:", with_rank[len(with_rank)/2][1], "Mb/device"
print "Max transfer by a single device:", with_rank[0][1], "Mb"
print "Min transfer by a single device (in sample):", with_rank[len(with_rank)-1][1], "Mb"

print "Generating plot..."

with open("with_rank.csv", "wb") as f:
    writer = csv.writer(f)
    writer.writerows(with_rank)

df = pd.read_csv("with_rank.csv")
df.columns = ['Rank', 'Mb']

ax = df.plot(logy=True, kind='line',x='Rank',y='Mb')

fig = ax.get_figure()
fig.savefig('device_tx_plot.png')
