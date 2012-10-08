Introduction
============

This package will contain utility scripts and configuration for launching and
maintaining lantern components that run on Amazon Web Services. 

At the moment only the infrastructure to launch, configure, and update cloud
instances is there.  There is nothing lantern-specific to this code so far.

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


