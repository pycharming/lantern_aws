#!/usr/bin/env python

from subprocess import *


if __name__ == '__main__':
    output = Popen(["lantern", "--version"], stdout=PIPE).communicate()[0]
    print output.split()[-1].rsplit('-', 1)[0]
