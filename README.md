Introduction
============

This package contains utility scripts and configuration files for launching and
maintaining Lantern components hosted on Amazon Web Services. 

## Overview

### Components

There are two types of systems created and managed by these scripts at this moment:

- **Lantern peers** AKA **invited servers**: EC2 instances that run Lantern in behalf of some user, providing fallback proxy access for their invitees (XXX: they are not called "invitee servers" only for consistency with older code-- this may need a cleanup.)

- **Invited server launchers**: this is a small fixed number of instances that launch and configure Lantern peers on demand.  For each such peer, they also build a correspending Lantern installer and upload them to S3.  These installers have the address of the corresponding peer baked in, so users that install Lantern from them can find the server even if Google Accounts and/or Google Talk are blocked.  Indeed, the main goal of these instances is providing access to Google Accounts/Talk whenever censors block it.

In addition, there is a script to create Amazon S3 buckets with random names, and register them with the **Lantern controller** so they can be used to host installers.

### How it works

#### Setup

To begin with, we call scripts to perform the following setup actions, in either order:

- create a pool of randomly named Amazon S3 buckets and register them with the **Lantern controller** ([like this](#create-buckets)), and

- [spawn](#spawn-invsrvlauncher) an invited server launcher.

#### Handling invitations

The first time each particular user (say, `inviter@gmail.com`) invites one of their buddies (say, `buddy@gmail.com`) to Lantern, the following happens:

 - The inviter's **Lantern client** sends an XMPP message (actually, an Available notification) to the **Lantern controller**, notifying it that `inviter@gmail.com` wants to invite `buddy@gmail.com`.  This request also includes some credentials (i.e. a *refresh token*) that allows the bearer to login to Google Talk as `inviter@gmail.com`.

 - **Lantern controller** chooses one of the least used buckets in its pool, and sends an SQS message to the **invited server launcher**, asking it to create a new **Lantern peer** that will run as the inviter.  To this end, it sends the refresh token it was passed from the Lantern client, and the name of the bucket where the installers created by this server should be stored.

 - The **invited server launcher** spawns and configures a new **Lantern peer** with the given refresh token, builds Lantern installers with that peer as the fallback server, and uploads them to a 'folder' with a randomly generated name in the given bucket.

 - The **Lantern peer** downloads all necessary packages and git repositories, builds Lantern itself and runs it as a service.

 - The **invited server launcher** notices that the lantern peer is done starting up and notifies the **lantern controller**, through a SQS message, of that fact, and of the location of the new installers (in the form `<bucket>/<folder>`).

 - The **Lantern controller** stores the installer location for `inviter@gmail.com` and sends an e-mail to `buddy@gmail.com` (and to whomever else may have been invited by `inviter@gmail.com` while the previous steps were taking place), telling them that they were invited, and where they can download a Lantern installer for their platform.

From here on, whenever `inviter@gmail.com` invites a new buddy, the invite e-mail will be sent immediately to them, using the installer location stored for the inviter.

## Usage

### Before you Start

These scripts require Python 2 (tested on 2.7.3; earlier versions may work)
and the 2.5 version of the [`boto`][boto] library.

As of this writing, the latest stable version of `boto` (2.6) **won't** work with these scripts.  You can run `bin/install-boto` to install an appropriate
version.

In addition, you need to let `boto` know your AWS credentials.  If you have an
`AWS_CREDENTIAL_FILE` environment variable set up as required by some AWS
command line tools, that should work.  Otherwise, you can set the following in
your .bashrc:

    AWS_ACCESS_KEY_ID - Your AWS Access Key ID

    AWS_SECRET_ACCESS_KEY - Your AWS Secret Access Key

or provide them through some of [boto's configuration files][botoconfig].

### <a id='secret'></a>Secret files

Most of the scripts described below take paths to sensitive files which, for security reasons, are not included in github.  If you need them, ask (e.g.) in the bns-ops mailing list.  After you obtain them, please [be careful][secguidelines] not to leak them.

[XXX: but how do you pass them to these scripts without having them unencrypted locally?]

### <a id='create-buckets'></a>Create buckets

To create and register a pool of buckets:

    bin/create_buckets.py <bucket count> <client secrets file> <refresh token file>

Where

- `bucket count` is the number of buckets we want to create;
- <a id='client-secrets-file'></a>`client secrets file` is the path to a [secret](#secret) file with the format and semantics described [here][client-secrets].  Typically, you download it from a link in the "API Access" section in the [Google APIs console][googleapiconsole]; 
- <a id='refresh-token-file'></a>`refresh token file` is the path to a [secret](#secret) file containing the *refresh token* that gives the app with the abovementioned *client secrets* permission to log in to Google Talk as `invsrvlauncher@gmail.com`.  [XXX: add to the repo a script to obtain this easily].

The script needs the latter two arguments in order to log into Google Talk as an user that the **Lantern controller** trusts, and send it an XMPP message to register the new buckets.

### <a id='spawn-invsrvlauncher'></a>Spawn an Invited Server Launcher

To launch, configure and start up an *invited server launcher*, you call `bin/spawn.py` with an annoyingly long list of arguments.  Most of these are files that the launcher needs only in order to pass them over to the Lantern peers it will launch:

    bin/spawn.py invsrvlauncher <stack name> <AWS credentials> <invsrvlauncher's id_rsa> <getexceptional key> <installer environment variables> <windows certificate> <OS X certificate> <lantern's id_rsa> <OAuth2 client secrets> <Fallback proxy keystore>

- `stack name` will be the name of the CloudFormation stack created for this server.  You can use this name to refer to this node in some of the finer grained scripts described [below](#plumbing).  This also allows you to identify the stack in any other interface to CloudFormation (e.g. the AWS web console).

- `invsrvlauncher's id_rsa` is a ssh private key for a `invsrvlauncher` github user.  The invitee server launcher needs to check out this very repository from github in order to launch Lantern peers, so this user has been given pull permissions.

- `AWS credentials` is a file containing credentials for an user with permissions to launch new CloudFormation stacks and create and populate S3 buckets. [XXX: pin down the exact permissions.]  The file should have the format expected by some AWS console tools at AWS_CREDENTIAL_FILE.  To wit:

        AWSAccessKeyId=UPPERCA5ELETTER5ANDNUMBERSHERE
        AWSSecretKey=bASe64+vOmIt/heRE

- `Lantern's id_rsa` is a ssh private key for a `lanterncyborg` github user.  At this moment this user has no permissions to our secret repositories, but the `lantern-ui` submodule is linked in the `lantern` repo with a ssh URI, so we need *some* ssh credentials that github recognizes.

- `OAuth2 client secrets` is the same as [above](#client-secrets-file).

- `getexceptional key` and the `install4j (...)` files contain various [secret](#secret) licensing information required to build the installers.

- `Fallback proxy keystore` is a file containing certificates needed by the fallback proxies so the client can verify their identity.

### <a id='spawn-lanternpeer'></a>Spawn a Lantern Peer

You are not supposed to launch Lantern peers during normal operation.  The invited server launcher does that.  But should you need this for debugging, testing, or recovery, this is how you do it:

    bin/spawn.py lantern-peer <stack name> <user credentials> <lantern's id_rsa> <OAuth2 client secrets> <Fallback proxy keystore>

Where

- `user credentials` is the path to a JSON file that contains the OAuth2 access credentials for the user in which behalf Lantern will run.  It has the form:

        {"username": "xyzzy@gmail.com",
         "access_token": "ya29.AHES6ZT ... ",
         "refresh_token": "1/G_aZr6_tIR ... "}

and all the other parameters are the same as their namesakes in the argument list for [spawning an invitee server launcher](#spawn-invsrvlauncher).

## <a id='plumbing'></a>Plumbing

There are separate scripts to launch, configure, and start up/update nodes.

### Launch

Launch a generic node running

    bin/launch_stack.py <stack type> <stack name>

where 

- `stack type` is either 'invsrvlauncher' or 'lantern-peer', and
- `stack name` is any valid CloudFormation stack name that is not already taken.  You may use this name in some of the scripts described below.

### Configure

Configure instance-specific data and copy over secret files using

    bin/init_files.py <stack type> <ip or stack name> <file>...

where

- `stack type` is either 'invsrvlauncher' or 'lantern-peer',
- `ip or stack name` is either the IP or stack name of the node you want to configure,

and the rest of the arguments are the same as you'd use with `spawn.py` for [either](#spawn-invsrvlauncher) [stack type](#spawn-lanternpeer).

If the stack type is 'lantern-peer', this script also tells the instance its public IP address and the port where it should listen for proxy requests.

### Bring up

Upload [salt][salt] configuration and trigger setup/update: 

    bin/update_node.py <stack type> <address>

Alternatively, you can update salt configuration for all instances of a given stack type by invoking:

    bin/update_group.py <stack type>


## To Do

Better provisions for recovery: what if a lantern-peer or bucket is discovered and blocked by censors?  At the moment everything gets set up alright in first place, but if you want to apply hotfixes you will need to rebuild/restart some stuff manually.  More details coming soon (TM).

Search for XXX in this document for other pending tasks.

[client-secrets]: https://developers.google.com/api-client-library/python/guide/aaa_client_secrets

[googleapiconsole]: https://code.google.com/apis/console/

[boto]: https://github.com/boto/boto 

[botoconfig]: http://code.google.com/p/boto/wiki/BotoConfig

[salt]: http://saltstack.org

[secguidelines]: https://github.com/getlantern/bns-ops/issues/5
