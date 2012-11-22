Introduction
============

This package contains utility scripts and configuration for launching and
maintaining lantern components that run on Amazon Web Services. 

At the moment you can launch a generic node using

  bin/launch-lantern-peer.py <node-name>

You initialize instance-specific data using

  bin/init-lantern-peer.py <client-secrets> <user-credentials>

Besides the data you explicitly provide, this tells the instance its public IP address and the port where it should listen for proxy requests.

Why is this step necessary?  The IP address is not known at the time of launch, so it cannot be provided when you run `launch-lantern-peer.py`.  Since it's also specific to each instance, there's no elegant way to provide it via a git push, so we can't do it in `update-group.py` either.  The other data could be provided on launch, but that would add one hack saving us nothing.

You can initialize all launched nodes as lantern instances using

  bin/update-group.py

The first time you run this, Oracle Java 7 and maven 3 will be installed, and the git HEAD of lantern will be checked out and built.  Subsequent updates will apply any changes in the salt configuration.

Still to do:

 - run lantern as a service, and
 - build and serve Lantern installers.

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

