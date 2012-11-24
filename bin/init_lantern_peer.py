#!/usr/bin/env python

import os
import shutil
import sys
import tempfile

import boto

expected_files = [
    ("client secrets", 'client_secrets.json'),
    ("user credentials", 'user_credentials.json'),
    ("installer environment variables", 'env-vars.txt'),
    ("windows certificate", 'bns_cert.p12'),
    ("OS X certificate", 'bns-osx-cert-developer-id-application.p12')]

verbose = False

def ec2_conn():
    try:
        return ec2_conn.conn
    except AttributeError:
        ec2_conn.conn = boto.connect_ec2()
        return ec2_conn.conn

def find_resource_id(resources, res_type):
    for res in resources:
        if res.resource_type == res_type:
            return res.physical_resource_id

def get_ip(resources):
    res_id = find_resource_id(resources, u'AWS::EC2::Instance')
    reservations = ec2_conn().get_all_instances(
                        instance_ids=[res_id],
                        filters={'group-name': 'lantern-peer'})
    if not reservations:
        return None
    instance, = reservations[0].instances
    return instance.ip_address

def get_port(resources):
    res_id = find_resource_id(resources, u'AWS::EC2::SecurityGroup')
    group, = ec2_conn().get_all_security_groups(groupnames=[res_id])
    rule, = group.rules
    assert rule.from_port == rule.to_port
    return rule.from_port

def run_critical(command, details):
    if os.system(command):
        print "FATAL ERROR:", details
        print "You probably want to troubleshoot this and retry.  Aborting."
        sys.exit(1)

def run(which, *paths):
    for (desc, expected_name), filename in zip(expected_files, paths):
        if not filename.endswith(expected_name):
            print "WARNING: I was kind of expecting the %s file to be called '%s'." % (desc, expected_name)
            print "Are you sure you provided them in the right order?"
            print "(%s)" % ", ".join(desc_ for (desc_, _) in expected_files)
            print "[y/N]:",
            if raw_input().strip().lower() != 'y':
                print "OK, try again with the right order."
                sys.exit(0)
            else:
                print "OK, nevermind."

    (client_secrets, user_credentials,
     installer_env_vars, windows_cert, osx_cert) = paths

    cf_conn = boto.connect_cloudformation()

    any_inited = False

    for stack in cf_conn.list_stacks():
        if stack.stack_status != 'CREATE_COMPLETE':
            if verbose:
                print ("(Ignoring stack '%s' with status %s.)"
                       % (stack.stack_name, stack.stack_status))
            continue
        resources = cf_conn.describe_stack_resources(stack.stack_id)
        ip = get_ip(resources)
        if ip is None:
            # There is no EC2 instance in this stack that belongs to the
            # `lantern-peer` security group, so this is not a lantern stack.
            if verbose:
                print "(Ignoring non-lantern stack '%s'.)" % stack.stack_name
            continue
        port = get_port(resources)
        print "Found live stack '%s' at %s:%s." % (stack.stack_name,
                                                   ip,
                                                   port)
        if which in ['all', stack.stack_name, ip]:
            tmpdir = tempfile.mkdtemp()
            try:
                host_path = os.path.join(tmpdir, 'host')
                port_path = os.path.join(tmpdir, 'port')
                file(host_path, 'w').write(ip)
                file(port_path, 'w').write(port)
                for (_, remote_filename), path \
                    in zip(expected_files, paths) + [((None, 'host'), host_path),
                                                     ((None, 'public-proxy-port'), port_path)]:
                    for command in [("scp %s lantern@%s:%s" % (path, ip, remote_filename)),
                                    ("ssh lantern@%s 'chmod 600 %s'" % (ip, remote_filename))]:
                        run_critical(command,
                                     "trying to copy/chmod %s to %s" % (path, remote_filename))
                print "Successfully initialized peer '%s' at %s." % (stack.stack_name, ip)
                run_critical("ssh lantern@%s 'mkdir secure; chmod 700 secure; mv *.p12 secure'" % ip,
                             "trying to relocate .p12 files at host %s." % ip)
            finally:
                shutil.rmtree(tmpdir)
            any_inited = True
        elif verbose:
            print "(Ignoring unselected peer '%s' at %s.)" % (stack.stack_name, ip)

    if not any_inited:
        if which == 'all':
            print "No `lantern-peer` stacks found."
        else:
            print ("No `lantern-peer` stack found, with name or ip '%s'."
                   % which)

def files_usage():
    return " ".join("<%s: %s>" % (filename, desc)
                    for desc, filename in expected_files)

if __name__ == '__main__':
    if len(sys.argv) != len(expected_files) + 2:
        print "Usage:", sys.argv[0], "<ip|stack_name|'all>", files_usage()
        sys.exit(1)
    run(*sys.argv[1:])
