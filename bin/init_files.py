#!/usr/bin/env python

import logging
import os
import shutil
import sys
import tempfile

import region


def get_private_ip(resources):
    res_id = find_resource_id(resources, u'AWS::EC2::Instance')
    reservations = ec2_conn().get_all_instances(instance_ids=[res_id])
    if not reservations:
        return None
    instance, = reservations[0].instances
    return instance.private_ip_address

def get_ip(resources):
    res_id = find_resource_id(resources, u'AWS::EC2::Instance')
    reservations = ec2_conn().get_all_instances(instance_ids=[res_id])
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

_common_files = [
    # DRY warning: invsrvlauncher's xmpp-bot.init relies on some of these
    # names.
    # XXX refactor out as constants when we have unified branches.
    ("lantern's id_rsa", 'lantern.id_rsa'),
    ("OAuth2 client secrets", 'client_secrets.json')]

configs = {
    'lantern-peer': {
        'user': 'lantern',
        'expected_files': [
            ("user credentials", 'user_credentials.json')]
            + _common_files,
        'computed_files': [
            ('host', get_ip),
            ('public-proxy-port', get_port)]},
    'invsrvlauncher': {
        'user': 'invsrvlauncher',
        'expected_files': [
            ("AWS credentials", '.aws_credential'),
            ("invsrvlauncher's id_rsa", 'invsrvlauncher.id_rsa'),
            ("getexceptional key", 'lantern_getexceptional.txt'),
            ("installer environment variables", 'env-vars.txt'),
            ("windows certificate", 'secure/bns_cert.p12'),
            ("OS X certificate", 'secure/bns-osx-cert-developer-id-application.p12')]
            + _common_files,
        'computed_files': []}}

def ec2_conn():
    try:
        return ec2_conn.conn
    except AttributeError:
        ec2_conn.conn = region.connect_ec2()
        return ec2_conn.conn

def find_resource_id(resources, res_type):
    for res in resources:
        if res.resource_type == res_type:
            return res.physical_resource_id


def run_critical(command, details):
    for tries in xrange(5):
        if not os.system(command):
            return
        time.sleep(5)
    logging.critical(details)
    raise RuntimeError

def run(stack_type, which, *paths):
    conf = configs[stack_type]
    for (desc, expected_path), filename in zip(conf['expected_files'], paths):
        expected_name = os.path.basename(expected_path)
        if not filename.endswith(expected_name):
            logging.warning("WARNING: I was kind of expecting the %s file to be called '%s'." % (desc, expected_name))

    cf_conn = region.connect_cloudformation()

    any_inited = False

    for stack in cf_conn.list_stacks():
        if stack.stack_status != 'CREATE_COMPLETE':
            continue
        resources = cf_conn.describe_stack_resources(stack.stack_id)
        ip = get_ip(resources)
        if ip is None:
            # There is no EC2 instance in this stack that belongs to the
            # `lantern-peer` security group, so this is not a lantern stack.
            continue
        if which in [stack.stack_name, ip]:
            logging.info("Found live stack '%s' at %s."
                         % (stack.stack_name, ip))
            push_files(conf, ip, paths, resources)
            logging.info("Successfully initialized peer '%s' at %s."
                         % (stack.stack_name, ip))
            any_inited = True
    if not any_inited:
        logging.warning(
            "No `lantern-peer` stack found, with name or ip '%s'." % which)

def push_files(conf, ip, paths, resources):
    tmpdir = tempfile.mkdtemp()
    try:
        for filename, fn in conf['computed_files']:
            path = os.path.join(tmpdir, filename)
            file(path, 'w').write(str(fn(resources)))
        for (_, remote_filename), path in zip(conf['expected_files'], paths):
            reldir, basename = os.path.split(remote_filename)
            if reldir:
                assert "/" not in reldir, "Deep paths not implemented yet."
                absdir = os.path.join(tmpdir, reldir)
                try:
                    os.mkdir(absdir, 0700)
                except OSError, e:
                    # Directory exists; ignore
                    if e.errno != 17:
                        raise
            else:
                absdir = tmpdir
            shutil.copyfile(path, os.path.join(absdir, basename))
        for root, dirs, files in os.walk(tmpdir):
            for filename in files:
                os.chmod(os.path.join(root, filename), 0600)
        user = conf['user']
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
    return " ".join("<%s: %s>" % (os.path.basename(filename), desc)
                    for desc, filename in expected_files)

if __name__ == '__main__':
    min_args = 3
    def error(tail):
        print "Usage:", sys.argv[0], "<instance-type> <ip|stack_name>", tail
        sys.exit(1)
    if len(sys.argv) < min_args:
        error("<required_file> [<required_file> ...]")
    instance_type = sys.argv[1]
    expected_files = configs[instance_type]['expected_files']
    if len(sys.argv) != len(expected_files) + min_args:
        error(files_usage(expected_files))
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')
    run(instance_type, *sys.argv[2:])
