#!/usr/bin/env python

import sys

import init_files


expected_files = [
    ("client secrets", 'client_secrets.json'),
    ("user credentials", 'user_credentials.json'),
    ("getexceptional key", 'lantern_getexceptional.txt'),
    ("installer environment variables", 'env-vars.txt'),
    ("windows certificate", 'secure/bns_cert.p12'),
    ("OS X certificate", 'secure/bns-osx-cert-developer-id-application.p12')]

#XXX: This is too frameworky, but avoids a lot of code duplication... :/
computed_files = [('host', init_files.get_ip),
                  ('public-proxy-port', init_files.get_port)]


if __name__ == '__main__':
    if len(sys.argv) != len(expected_files) + 2:
        print "Usage:", sys.argv[0], "<ip|stack_name>",
        print init_files.files_usage(expected_files)
        sys.exit(1)
    init_files.run('lantern', expected_files, computed_files, *sys.argv[1:])
