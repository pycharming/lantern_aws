#!/usr/bin/env python

from collections import defaultdict
import sys

import yaml


def pick_good(vals):
    for i in xrange(0, len(vals), 30):
        print
        for j, v in enumerate(vals[i:i+30]):
            print "%s: %s" % (j, v)
        while True:
            resp = raw_input("Which of the above looks good? (hit ENTER if none)")
            if not resp:
                break
            try:
                iresp = int(resp)
            except ValueError:
                print "Please enter a number or just hit ENTER."
                continue
            return vals[i + iresp]

def run():
    d = yaml.load(file('result'))
    print "%s left to check" % len(d)
    try:
        expected = file('expected').read()
    except IOError:
        expected = pick_good(d.values())
        file('expected', 'w').write(expected)
    bad = [(n, r) for n, r in d.iteritems() if r != expected]
    print
    print "Got %s bad ones:" % len(bad)
    histogram = defaultdict(int)
    for _, r in bad:
        histogram[r] += 1
    ones = sum(1 for _, times in histogram.iteritems() if times == 1)
    if ones <= 10:
        min_times = 1
    else:
        min_times = 2
    ranking = [(times, txt) for txt, times in histogram.iteritems()
               if times >= min_times]
    ranking.sort()
    ranking.reverse()
    for times, txt in ranking:
        print "    %s occurrences of %r" % (times, txt)
    if ones > 10:
        print "...and %s single items" % ones
    file('bad', 'w').write(','.join(n for n,r in bad))


if __name__ == '__main__':
    run()
