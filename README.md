Introduction
============

This package contains utility scripts and configuration for launching and
maintaining lantern components that run on Amazon Web Services. 

## Short version

Launch, configure and start up a lantern node by running:

    bin/spawn.py <node-name> <client-secrets-file> <user-credentials-file> <getexceptional-key> <install4j-env-vars> <install4j-windows-key> <install4j-osx-key>

`node-name` will be the name of the CloudFormation stack created for this node.  You can use this name to refer to this node in some of the finer grained scripts described in the next section.  This also allows you to identify the stack in any other interface to CloudFormation (e.g. the AWS web console).

`client-secrets-file` is the path to a JSON file in the format Google Apps makes available for download when you register an application.

`user-credentials` is the path to a JSON file that contains the OAuth2 access credentials for the user in which behalf Lantern will run.  It has the form:

    {"username": "xyzzy@gmail.com",
     "access_token": "ya29.AHES6ZT ... ",
     "refresh_token": "1/G_aZr6_tIR ... "}

`getexceptional-key` and the `install4j-*` files contain various licensing information required to build the installers.

### Shorter version

If you copy the install4j files to the examples folder, the following command will launch an instance with client secrets and user credentials associated to some lanterncyborg@gmail.com:

    example/spawn <node-name>

*Update:* This user is not in beta, though.
 
## For finer control

There are separate scripts to launch, configure, and start up lantern nodes.

Launch a generic node running

    bin/launch_stack.py <node-name>

Configure instance-specific data running

    bin/init_lantern_peer.py <client-secrets> <user-credentials> <install4j-env-vars> <install4j-windows-key> <install4j-osx-key>

Besides the data you explicitly provide, this tells the instance its public IP address and the port where it should listen for proxy requests.

Setup/update all launched nodes as lantern instances using

    bin/update_group.py

This will do nothing to instances that are already up to date.

Alternatively, initialize/update a specific node using

    bin/update_node.py <address>

The first time you run either update script, Oracle Java 7, maven 3 and install4j will be installed, installers will be built, the 'oauth2' branch of Lantern will be checked out and built, and Lantern will be launched as a service.  Subsequent updates will apply any changes in the [salt][salt] configuration.

## To Do

Better dependency management.  At the moment everything gets set up alright in first place, but if you want to apply hotfixes you will need to rebuild/restart some stuff manually.  More details coming soon (TM).

Before you Start
================

These scripts require Python 2 (tested on 2.7.3; earlier versions may work)
and the 2.5 version of the [`boto`][boto] library.

As of this writing, the latest version of `boto` (2.6) **won't** work with
these scripts.  You can run `bin/install-boto` to install an appropriate
version from GitHub.

In addition, you need to let `boto` know your AWS credentials.  If you have an
`AWS_CREDENTIAL_FILE` environment variable set up as required by some AWS
command line tools, that should work.  Otherwise, you can set the following in
your .bashrc:

    AWS_ACCESS_KEY_ID - Your AWS Access Key ID

    AWS_SECRET_ACCESS_KEY - Your AWS Secret Access Key

or provide them through some of [boto's configuration files][botoconfig].


[boto]: https://github.com/boto/boto 

[botoconfig]: http://code.google.com/p/boto/wiki/BotoConfig

[salt]: http://saltstack.org
