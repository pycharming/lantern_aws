# Lantern Cloud

This project contains code and configuration scripts to launch and manage cloud servers to provide functionality for the [Lantern](https://github.com/getlantern/lantern) censorship circunvention tool.

At this moment, two types of machines are launched and managed by this project:

- Lantern Peers, which double as kaleidoscope nodes in behalf of some inviter, and provide fallback proxying to Lantern users.  The latter is necessary because in order to authenticate into the Lantern system a client needs access to Google Accounts and Google Talk, which may be blocked in censoring countries.

- A single Cloud Master, which launches lantern peers on request from the [Lantern Controller](https://github.com/getlantern/lantern-controller).  [The following is not implemented as of this writing]  Further operations on lantern peers (especially 'batch' operations involving many such machines) will typically be done through this cloud master.

The Cloud Master also builds and uploads Lantern installers configured to use a specific host and port for fallback proxying.  [This scheme will be replaced soon by one in which the Lantern peers build and upload small programs (called installer wrappers) that download a Lantern installer, install Lantern from it, and configure it to use the appropriate fallback proxy.]

As of this writing, only EC2 machines are supported, but it should be easy to add support for any cloud provider that offers Ubuntu 12.04 and is supported by [Salt Cloud](https://github.com/saltstack/salt-cloud).

## How does it work

Cloud masters listen for SQS messages from the Lantern Controller, launch EC2 Lantern peers on demand, build and upload installers, and notify Lantern Controller through a SQS message when all is set up for one inviter. 

Lantern peers download, install and run a Lantern client, with some command line arguments instructing it to provide fallback proxying to unauthenticated peers.

[Salt](http://saltstack.com/) is used for configuration management.  The `salt` directory in this project contains the configuration for all the machines (you can see which modules apply to which machines in `salt/top.sls`).  [Salt Cloud](https://github.com/saltstack/salt-cloud) is used to launch the machines, and the Cloud Master doubles as a Salt Master for launched peers, so they fetch their initial configuration from them.

## Usage

### Before you start

You need a recent version of Boto to run the script that launches cloud masters.

    sudo pip install boto

After you check out this repository you need to run the following to fetch secrets required by Lantern:

    git submodule update --init

Note that this downloads a private repository that is only accessible to the Lantern core development team.  (XXX:) Instructions to replace these secrets with your own equivalents will be added here soon(TM).

[XXX: fallback proxy certs (keystores) are not in the secret repo, but we are feeding them manually to the Cloud Master.  Consider using the same scheme for all secret files.] 

### Launching a cloud master

You launch a cloud master using the following command: 

    bin/launch.py

By default, this will launch an instance with name 'cloudmaster' in the `ap-southeast-1` (Singapore) region.  This instance will communicate with the production Lantern Controller (app engine ID `lanternctrl`).  It will also use a security group called 'free-for-all', which is expected to be totally open (access will be restricted through in-machine firewalls).  This security group will be created if it's not found in the given region.  You can modify all the values described in this paragraph editing `config.py`.

As of this writing, allowed regions are

    ap-southeast-1 (default)
    us-east-1 (useful for testing).

Should you want to add support for other regions, just create a `lantern` KeyPair in that region and upload the corresponding `.pem` file to `getlantern/too-many-secrets/lantern_aws/<region-id>.pem`.

The cloud master will use the Salt configuration in your local `salt/` directory (i.e., not a git commit of any sort).

### Updating a cloud master

You can sync the Salt configuration of the cloud master (and therefore of Lantern peers too) with the one in your local `salt/` directory (i.e., not a git commit of any sort), and trigger that cloud master and all machines managed by it to update themselves to the new configuration, using the following command:

    bin/update.py

The region and controller ID in `config.py` will be used to find the Cloud Master to update.

## Todo

Update lantern peers when new installer versions come up.

Move to installer wrapper scheme.

Script to reparent orphaned lantern peers if cloud master dies catastrophically (note: we can probably repurpose some script from the salt-cloud codebase).
