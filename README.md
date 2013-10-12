# Lantern Cloud

**WARNING**: Restarting the lantern service (which is done automatically by the salt scripts on some circumstances) will kill all java processes in the fallback proxy.  As of this writing there are no other java processes, but if you want to add any, keep this in mind.

This project contains code and configuration scripts to launch and manage cloud servers for the [Lantern](https://github.com/getlantern/lantern) censorship circunvention tool.

At this moment, two types of machines are launched and managed by this project:

- **Fallback Proxies**: These run Lantern instances configured to offer access to the free internet to Lantern users that haven't authenticated yet so they can reach Google Accounts and Google Talk in order to do so.  They also double as regular kaleidoscope nodes in behalf of some inviter.  On setup, these machines also build and upload *installer wrappers*, small programs that users run to install Lantern and help it find the corresponding fallback proxy.

- A single **Cloud Master**, which launches lantern peers on request from the [Lantern Controller](https://github.com/getlantern/lantern-controller).  Further operations on lantern peers (especially 'batch' operations involving many such machines) are typically done through this cloud master.

As of this writing, only EC2 and Digital Ocean machines are supported, but it should be easy to add support for any cloud provider that offers Ubuntu 12.04 and is supported by [Salt Cloud](https://github.com/saltstack/salt-cloud).

## How does it work

Whenever a Lantern user first invites someone, the Lantern Controller sends a message to an SQS queue, requesting that a fallback proxy corresponding to this user be launched.  Cloud masters listen for such messages and launch fallback proxies in response.

Fallback proxies build and upload installer wrappers, and they download, install and run a Lantern client, with some command line arguments instructing it to run as a fallback proxy in behalf of the given user.  When done, they notify the Lantern Controller by sending a message to another SQS queue, and then they delete the original SQS message that triggered the whole operation.

If the fallback proxy fails to set itself up, eventually the SQS message that triggered its launch will become visible again for the cloud master.  When a cloud master finds that an EC2 instance already exists for the user referred to in a launch request, it will assume that the fallback proxy has failed to complete setup correctly due to temporary conditions, so it will kill it and launch a new one (this is a bit brutish; in theory the proxy should be able to recover by attempting again to apply the Salt state.  We may try that in the future).

[Salt](http://saltstack.com/) is used for configuration management.  The `salt` directory in this project contains the configuration for all the machines (you can see which modules apply to which machines in `salt/top.sls`).  [Salt Cloud](https://github.com/saltstack/salt-cloud) is used to launch the machines, and the Cloud Master doubles as a Salt Master for launched peers, so they fetch their initial configuration from it.

## Usage

### Before you start

You need a recent version of Boto to run the script that launches cloud masters.

    sudo pip install boto

After you check out this repository you need to run the following to fetch secrets required by Lantern:

    git submodule update --init

Note that this downloads a private repository that is only accessible to the Lantern core development team.

Finally, you need an up-to-date checkout of the `getlantern/lantern` project placed as a sibling of this one.

(XXX:) Instructions to replace these secrets with your own equivalents will be added here on request to aranhoide@gmail.com.

[XXX: fallback proxy certs (keystores) are not in the secret repo, but we are feeding them manually to the Cloud Master.  Consider using the same scheme for all secret files.] 

### Launching a cloud master

You launch a cloud master using the following command: 

    bin/launch_cloudmaster.py

By default, this will launch an instance with name 'cloudmaster' in the `ap-southeast-1` (Singapore) region.  This instance will communicate with the production Lantern Controller (app engine ID `lanternctrl`).  It will also use a security group called 'free-for-all', which is expected to be totally open (access will be restricted through in-instance firewalls).  This security group will be created if it's not found in the given region.  You can modify all the values described in this paragraph editing `config.py`.

As of this writing, allowed regions are

    ap-southeast-1 (default)
    us-east-1 (useful for testing).

Should you want to add support for other regions, just create a `lantern` KeyPair in that region and upload the corresponding `.pem` file to `getlantern/too-many-secrets/lantern_aws/<region-id>.pem`.

The cloud master will use the Salt configuration in your local `salt/` directory (i.e., not a git commit of any sort).

### Updating a cloud master

You can sync the Salt configuration of the cloud master (which is the one that all launched peers use) with the one in your local `salt/` directory (i.e., not a git commit of any sort), using the following command:

    bin/update.py

The region and controller ID in `config.py` will be used to find the Cloud Master to update.

#### Applying the updated configuration

Note that `bin/update.py` doesn't apply the changes.  Sometimes you only want to upload your salt config in order to update the fallback proxies (or even one particular proxy), or only the cloud master, or all of them.  You can do that after you sync the cloud master with your local Salt configuration.

You apply the new configuration by using regular salt commands.  As a convenience, a `bin/ssh_cloudmaster.py [<command>]` script will find your cloud master and run the command you provide there, or just log you in as the `ubuntu` user if you provide no commands (the `lantern` user would perhaps be more convenient, but it wouldn't work for cloud masters that haven't been configured yet, or from machines without SSH keys that our setup recognizes).

So, for example, to sync the cloudmaster only to the current configuration:

    bin/ssh_cloudmaster.py 'sudo salt-call state.highstate'

To sync all machines (including the cloud master itself):

    bin/ssh_cloudmaster.py 'sudo salt "*" state.highstate'

All fallback proxies have salt IDs (and EC2 names) starting with 'fp-', so you can instruct the proxies, but not the cloud master, to apply the current configuration with

    bin/ssh_cloudmaster.py 'sudo salt "fp-*" state.highstate'

To run an arbitrary command (as root) in all fallback proxies:

    bin/ssh_cloudmaster.py 'sudo salt "fp-*" cmd.run "ls /home/lantern/"'

##### Common tasks

Tasks will be added here in a per need basis.

###### Listing nonresponding fallbacks

These may need further looking into.  It might be a good idea to run this before important updates.
```
./ssh_cloudmaster.py 'sudo salt-run manage.down'
```

###### Listing the user as which each fallback proxy is running
```
./ssh_cloudmaster.py 'sudo salt "fp-*" pillar.get user'
```

###### List all proxies running as a given user

```
./ssh_cloudmaster.py 'sudo salt -I "user:adamfisk@smartfil.es" test.ping'
```

###### Rebuilding wrappers

The fallback proxies keep track of the completion status of the different subtasks by using flag files in the `/home/lantern` directory.  These are:

- `/home/lantern/wrappers_built` signals that wrappers have been built,
- `/home/lantern/uploaded_wrappers` signals that wrappers have been uploaded, and
- `/home/lantern/reported_completion` signals that we have notified lantern-controller that this server is up (and where to find the wrappers).

In order to trigger any of these operations again, you just delete the file that flags its completion and ask the machine to apply its Salt config again.  For example, to request that all wrappers be rebuilt, uploaded again, and that lantern-controller be notified of the new locations so it will send new invite e-mails out, you say:

    bin/ssh_cloudmaster.py 'sudo salt "fp-*" cmd.run "rm /home/lantern/wrappers_built /home/lantern/uploaded_wrappers /home/lantern/reported_completion ; salt-call state.highstate"'

Since this turned out to be needed quite often, a `bin/rebuild_wrappers.bash` script has been added that does just this.

###### Reinstalling lantern

To reinstall lantern in the proxies after a new client version has been released, just uninstall the old package through `apt-get` and then run `state.highstate` to re-apply the configuration scripts.  This takes care of restarting the lantern service too.  `bin/reinstall_lantern.bash` (which see) does this.

**WARNING**: Restarting the lantern service (which is done automatically by the salt scripts when reinstalling lantern, and possibly on some other circumstances) will kill all java processes in the fallback proxy.  As of this writing there are no other java processes, but if you want to add any, keep this in mind.

## Todo

Script to reparent orphaned lantern peers if cloud master dies catastrophically (note: we can probably repurpose some script from the salt-cloud codebase).
