 # Lantern Cloud

This project contains code and configuration scripts to launch and manage cloud-hosted infrastructure for the [Lantern](https://github.com/getlantern/lantern) censorship circumvention tool.

At this moment, three types of machines are launched and managed by this project:

- **Fallback Proxies**: These run Lantern instances to offer access to the
  free internet to Lantern users that have no available peers for this end.

- **Flashlight Servers**: These serve a similar role as fallback proxies, but
  they use [domain fronting](https://trac.torproject.org/projects/tor/wiki/doc/meek) for extra blocking resistance.

- A single **Cloud Master**, which launches fallback proxies on request from the [Lantern Controller](https://github.com/getlantern/lantern-controller).  Further operations on fallback proxies (especially 'batch' operations involving many such machines) are typically done through this cloud master.

As of this writing, only EC2 and Digital Ocean machines are supported, but it should be easy to add support for any cloud provider that offers Ubuntu 12.04+ and is supported by [Salt Cloud](https://docs.saltstack.com/en/latest/topics/cloud/).

## How does it work

Whenever we determine a new server needs to be launched or destroyed, a new message is sent to an SQS queue encoding a request.  We can do this manually (see `bin/fake_controller.py` or, in the case of fallbacks, the controller may do it on its own.  Cloud masters listen for such messages and perform the requested operations.

Fallback proxies download, build and run a Lantern client, with some command line arguments instructing it to proxy traffic to the uncensored internet.  When done with setup, they notify the Lantern Controller by sending a message to another SQS queue, and then they delete the original SQS message that triggered the whole operation.

If the fallback proxy fails to set itself up, eventually the SQS message that triggered its launch will become visible again for the cloud master.  When a cloud master finds that an instance already exists with the same ID as that in a launch request, it will assume that it has failed to complete setup correctly due to temporary conditions, so it will kill it and launch a new one.

[Salt](http://saltstack.com/) is used for configuration management.  The `salt` directory in this project contains the configuration for all the machines (you can see which modules apply to which machines in `salt/top.sls`).  [Salt Cloud](https://docs.saltstack.com/en/latest/topics/cloud/) is used to launch the machines, and the Cloud Master doubles as a Salt Master for launched peers, so they fetch their initial configuration from it.

## Usage

### Before you start

You need a recent version of the Digital Ocean API Python wrapper to run the script that launches cloud masters.

    sudo pip install -U python-digitalocean

After you check out this repository, and unless you passed the `--recursive` flag to `git clone`, you need to run the following to fetch secrets required by Lantern:

    git submodule update --init

Note that this downloads a private repository that is only accessible to the Lantern core development team.

(XXX:) Instructions to replace these secrets with your own equivalents will be added here on request to aranhoide@gmail.com.

### Launching a cloud master

You launch a cloud master using the following command:

    bin/launch_cloudmaster.py

By default, this will launch an instance with name 'cloudmaster1-2' (historical reasons) in the `sgp1` (Singapore 1) Digital Ocean datacenter.  This instance will communicate with the production Lantern Controller (app engine ID `lanternctrl1-2`).  You can modify all the values described in this paragraph by editing `bin/launch_cloudmaster.py` itself and/or creating `bin/config_overrides.py` to override values in `bin/config.py`.  Note that this file is not managed by git.

The cloud master will use the Salt configuration in your local `salt/` directory (i.e., not a git commit of any sort).

#### Example `config_overrides.py`

```
controller = 'oxlanternctrl'
cloudmaster_name = 'oxcloudmaster'
```

### Updating a cloud master

You can sync the Salt configuration of the cloud master (which is the one that all launched peers use) with the one in your local `salt/` directory (i.e., not a git commit of any sort), using the following command:

    bin/update.py

The values in `config.py` will be used to find the Cloud Master to update.

#### Applying the updated configuration

Note that `bin/update.py` doesn't apply the changes to the machines managed by Salt.  Sometimes you only want to upload your salt config in order to update the fallback proxies (or even one particular proxy), or only the cloud master, or all of them.  You can do that after you sync the cloud master with your local Salt configuration.

You apply the new configuration by using regular salt commands.  As a convenience, a `bin/ssh_cloudmaster.py [<command>]` script will find your cloud master and run the command you provide there, or just log you in as the root user if you provide no commands.

So, for example, to sync the cloudmaster only to the current configuration:

    bin/ssh_cloudmaster.py 'sudo salt-call state.highstate'

or, as a shortcut,

    bin/hscloudmaster.bash

To sync all machines (including the cloud master itself):

    bin/ssh_cloudmaster.py 'salt -b 5 "*" state.highstate'

where the `-b 5` part does some batching to avoid overloading the cloudmaster.

All fallback proxies have salt IDs starting with 'fp-', so you can instruct the proxies, but not the cloud master, to apply the current configuration with

    bin/ssh_cloudmaster.py 'salt -b 5 "fp-*" state.highstate'

or, as a shortcut,

    bin/histate.bash

To run an arbitrary command (as root) in all fallback proxies:

    bin/ssh_cloudmaster.py 'salt "fp-*" cmd.run "ls /home/lantern/"'

##### Common tasks

Tasks will be added here in a per need basis.  You may want to check out the `bin` folder for example scripts.

###### Listing nonresponding fallbacks

These may need further looking into.  It might be a good idea to run this before important updates.  That said, the cloudmaster checks these regularly and sends alarm emails to the Lantern team when they fail to respond.

    bin/ssh_cloudmaster.py 'sudo salt-run manage.down'

or, in short,

    bin/check_unresponsive_fallbacks.bash

###### List the ips with wich each fallback proxy is running

    bin/fp-ips.bash

###### Launch a fallback proxy with fteproxy enabled
```
bin/fake_controller.py launch "ox@getlantern.org" 102 '{"pt_type": "FTE", "pt_props": { "key": "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF0000000000000000000000000000000F", "upstream-regex": "^GET\\ \\/([a-z\\.\\/]*) HTTP/1\\.1\\r\\n\\r\\n$", "downstream-regex": "^HTTP/1\\.1\\ 200 OK\\r\\nContent-Type:\\ ([a-z]+)\\r\\n\\r\\n\\C*$" }}'
```

###### Launch a flashlight server
```
bin/fake_controller.py launch-fl fl-singapore-001-15
```

###### Launch a waddell server
```
bin/fake_controller.py launch-wd wd-001-1
```

###### Reinstalling lantern

To reinstall lantern in the proxies after a new client version has been released, just uninstall the old package through `apt-get` and then run `state.highstate` to re-apply the configuration scripts.  This takes care of restarting the lantern service too.  `bin/reinstall_lantern.bash` (which see) does this.
