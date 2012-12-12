# XXX: There is stuff here that is specific to lantern peers (specifically,
# feeding ip and port in addition to the given files).  It doesn't hurt for
# other instances, but I'd better factor it out for clarity.

import os
import shutil
import sys
import tempfile

import boto


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
    # XXX: this stuff is specific to lantern peers.  It doesn't
    # hurt for other instances, but I'd better factor it out.
    res_id = find_resource_id(resources, u'AWS::EC2::Instance')
    reservations = ec2_conn().get_all_instances(
                        instance_ids=[res_id],
                        filters={'group-name': 'lantern-peer'})
    if not reservations:
        return None
    instance, = reservations[0].instances
    return instance.ip_address

def get_port(resources):
    # XXX: this stuff is specific to lantern peers.  It doesn't
    # hurt for other instances, but I'd better factor it out.
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

def run(user, expected_files, which, *paths):
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
        if which in ['all', stack.stack_name, ip]:
            port = get_port(resources)
            print "Found live stack '%s' at %s:%s." % (stack.stack_name, ip, port)
            push_files(user, expected_files, ip, port, paths)
            print "Successfully initialized peer '%s' at %s." % (stack.stack_name, ip)
            any_inited = True
        elif verbose:
            print "(Ignoring unselected peer '%s' at %s.)" % (stack.stack_name, ip)

    if not any_inited:
        if which == 'all':
            print "No `lantern-peer` stacks found."
        else:
            print ("No `lantern-peer` stack found, with name or ip '%s'."
                   % which)

def push_files(user, expected_files, ip, port, paths):
    tmpdir = tempfile.mkdtemp()
    try:
        secure = os.path.join(tmpdir, 'secure')
        os.mkdir(secure, 0700)
        host_path = os.path.join(tmpdir, 'host')
        port_path = os.path.join(tmpdir, 'public-proxy-port')
        file(host_path, 'w').write(ip)
        file(port_path, 'w').write(port)
        for (_, remote_filename), path in zip(expected_files, paths):
            d = secure if remote_filename.endswith(".p12") else tmpdir
            shutil.copyfile(path, os.path.join(d, remote_filename))
        for root, dirs, files in os.walk(tmpdir):
            for filename in files:
                os.chmod(os.path.join(root, filename), 0600)
        tbz = shutil.make_archive(os.path.join(tmpdir, 'init-data'),
                                  'bztar', tmpdir, '.')
        run_critical("scp -o 'StrictHostKeyChecking no' %s %s@%s:"
                                                 % (tbz, user, ip),
                     "trying to copy files.")
        bn = os.path.basename(tbz)
        run_critical("ssh %s@%s 'tar xvfj %s && rm %s'" % (user, ip, bn, bn),
                     "trying to extract files.")
    finally:
        shutil.rmtree(tmpdir)

def files_usage(expected_files):
    return " ".join("<%s: %s>" % (filename, desc)
                    for desc, filename in expected_files)
