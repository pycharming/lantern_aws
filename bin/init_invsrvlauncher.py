#!/usr/bin/env python

import sys

import init_files


expected_files = [("AWS credentials", '.aws_credentials')]


if __name__ == '__main__':
    if len(sys.argv) != len(expected_files) + 2:
        print "Usage:", sys.argv[0], "<ip|stack_name|'all>",
        print init_files.files_usage(expected_files)
        sys.exit(1)
    init_files.run('invsrvlauncher', expected_files, *sys.argv[1:])
