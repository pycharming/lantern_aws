#!/usr/bin/env python

import sys

import util


if __name__ == '__main__':
    util.ssh_cloudmaster(*sys.argv[1:])
