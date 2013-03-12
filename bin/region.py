import boto
from boto.regioninfo import RegionInfo
from boto.ec2.connection import EC2Connection
from boto.cloudformation.connection import CloudFormationConnection
from boto.s3.connection import S3Connection


default_region = 'ap-southeast-1'

classes = {'ec2': EC2Connection,
           'cloudformation': CloudFormationConnection,
           's3': S3Connection}


def make_connect(service_name):
    def connect(region_name=default_region):
        return RegionInfo(None,
                          region_name,
                          "%s.%s.amazonaws.com" % (service_name, region_name),
                          classes[service_name]).connect()
    return connect

connect_ec2 = make_connect('ec2')
connect_cloudformation = make_connect('cloudformation')
connect_s3 = make_connect('s3')
