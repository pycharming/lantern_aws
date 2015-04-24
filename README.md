 # Lantern Cloud

This project contains code and configuration scripts to launch and manage cloud-hosted infrastructure for the [Lantern](https://github.com/getlantern/lantern) censorship circumvention tool.

At this moment, three types of machines are launched and managed by this project:

- **Fallback Proxies**: These run Lantern instances to offer access to the
  free internet to Lantern users that have no available peers for this end.

- **Flashlight Servers**: These serve a similar role as fallback proxies, but
  they use [domain fronting](https://trac.torproject.org/projects/tor/wiki/doc/meek) for extra blocking resistance.

- A single **peerscanner**, which checks that flashlight servers are up and
  maintains their DNS entries.

- [soon] **waddell servers**: which offer lightweight messaging between
  lantern-related clients and services.

- A single **Cloud Master**, which launches fallback proxies on request from the [Lantern Controller](https://github.com/getlantern/lantern-controller), or any of the other previously mentioned server types, on request from administrators (see `bin/fake_controller.py`).  Further operations on fallback proxies (especially 'batch' operations involving many such machines) are typically done through this cloud master.

As of this writing, only Digital Ocean machines are supported, but it should be easy to add support for any cloud provider that offers Ubuntu 12.04+ (although 14.04 is preferred) and is supported by [Salt Cloud](https://docs.saltstack.com/en/latest/topics/cloud/).

## How does it work

Whenever we determine a new server needs to be launched or destroyed, a new message is sent to an SQS queue encoding a request.  We can do this manually (see `bin/fake_controller.py`) or, in the case of fallbacks, the controller may do it on its own.  Cloud masters listen for such messages and perform the requested operations.

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

By default, this will launch an instance with name 'production-cloudmaster' in the `sgp1` (Singapore 1) Digital Ocean datacenter.  This instance will communicate with the production Lantern Controller (app engine ID `lanternctrl1-2`).  You can modify all the values described in this paragraph by creating `bin/config_overrides.py` to override values in `bin/config.py`.  Note that this file is not managed by git.

The cloud master will use the Salt configuration in your local `salt/` directory (i.e., not a git commit of any sort).  But you can only deploy to the production cloudmaster from a clean master checkout.

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

If you are not sure whether a configuration change requires applying the
changes in the cloudmaster itself, it can't hurt to just do it to be in the safe side.

To sync all machines (including the cloud master itself):

    bin/ssh_cloudmaster.py 'salt -b 20 "*" state.highstate'

where the `-b 20` part does some batching to avoid overloading the cloudmaster.

All fallback proxies have salt IDs starting with 'fp-', so you can instruct the proxies, but not the cloud master, to apply the current configuration with

    bin/ssh_cloudmaster.py 'salt -b 5 "fp-*" state.highstate'

or, as a shortcut,

    bin/histate.bash

To run an arbitrary command (as root) in all fallback proxies:

    bin/ssh_cloudmaster.py 'salt "fp-*" cmd.run "ls /home/lantern/"'

##### Common tasks

Tasks will be added here in a per need basis.  You may want to check out the `bin` folder for example scripts.

###### Perform basic checks on newly launched minions

Once you have launched a minion by any of the methods described below, the
machine will start applying the Salt configuration on its own.  A common
problem when first testing configuration changes is that Salt rejects your .sls 
files altogether (for example, if you have some YAML or Jinja syntax error).
One way to quickly detect that is to run

    bin/ssh_cloudmaster.py 'salt <your-machine-id> state.highstate'

If your .sls files have errors, the output of this command will make that
clear.  If, on the contrary, you get something like this:

    fp-test-001:
        Data failed to compile:
    ----------
        The function "state.highstate" is running as PID 4120 and was started at  with jid req

then at least the syntax seems OK.  If you have nothing better to do, you can make sure progress is being made by periodically running:

    bin/ssh_cloudmaster.py 'salt <your-machine-id> cmd.run 'tail -n 40 /var/log/salt/minion'

and making sure that new stuff keeps getting printed.

If all you want to know is whether the machine(s) are done setting themselves
up (e.g., you haven't made any config changes), you can run something like
(e.g., for flashlight servers)

    bin/ssh_cloudmaster.py 'salt "fl-20150327-*" cmd.run "service flashlight status"'

If you expect to run a lot of these it will be faster log into the
cloudmaster (just 'bin/ssh_cloudmaster.py` without arguments) and run the
commands from there.

###### Listing nonresponding minions

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
bin/fake_controller.py launch-fl fl-sg-20150226-001
```

The naming convention is `fl-<datacenter>-<date of launch>-<serial number>`,
where

- datacenter is some string uniquely identifying the datacenter where the server is launched (see below for instructions on how to launch minions to different data centers);
- date of launch is in YYYYMMDD format; and
- serial numbers are zero-filled to three positions (that is, `-001` rather than just `-1`), and reset to start at 001 for each launch day.

**Launching to a particular datacenter**

The list of currently available datacenter and size combinations is in `salt/salt_cloud/cloud.profiles`.  If the datacenter+size combination you want is already there, you can launch one minion there by adding the profile name as a third argument to `bin/fake_controller.py`, e.g.:

    bin/fake_controller.py launch-fl fl-nl-20150226-001 do_nl

If the location you want is not there, it shouldn't be hard to add a different
one to `salt/salt_cloud/cloud.providers`.  To get a list of available Digital
Ocean datacenters, try `bin/do_fps.py print_regions`.  If several datacenters
are available in one location, the one with the highest number (e.g.
"Amsterdam 3" as opposed to "Amsterdam 1") will be more likely to have private
network capabilities and perhaps more modern hardware (but it can't hurt to
try and compare).

Once the location you want is in `cloud.providers`, if the size you want is
not in `salt/salt_cloud/cloud.profiles` you need to add it; see the entries
already there for reference.  If there is no entry with the size you want, try
`bin/do_fps.py print_sizes` (or just take a guess if you feel lucky; they're
named rather consistently).

If you have changed either configuration file, you will need to push and apply
your new configuration to the cloudmaster.  If you're deploying to the
production cloudmaster, you will need to first commit, pull, and push your changes to the master branch, lest you accidentally roll back someone else's changes or vice versa.  Once you are done, do `bin/update.py && bin/hscloudmaster.bash`.  If no errors are reported, you're ready to deploy your new servers as explained above.

###### Launch a waddell server
```
bin/fake_controller.py launch-wd wd-001-1
```

###### Reinstalling lantern

To reinstall lantern in the proxies after a new client version has been released, just uninstall the old package through `apt-get` and then run `state.highstate` to re-apply the configuration scripts.  This takes care of restarting the lantern service too.  `bin/reinstall_lantern.bash` (which see) does this.

###### Regenerating flashlight/genconfig/fallback.json

Whenever you launch or kill fallback proxies, you should update the list of
chained servers in the configuration that gets pushed to Lantern clients.  This
list lives in flashlight/genconfig/fallbacks.json.  To update it run

    bin/ssh_cloudmaster.py regenerate-fallbacks-list > <flashlight-root>/genconfig/fallback.json

Where `<flashlight-root>` is where your checkout of the flashlight project
lives (at the time of this writing, you may want to actually update the
flashlight checkout within the `lantern` project instead.

## Troubleshooting

These pain points can and will be removed soon (TM).

### The cloudmaster doesn't seem to be picking up my launch requests

If this is a test cloudmaster and the associated controller doesn't exist,
it's possible that the SQS queue doesn't exist.  Try creating one in the AWS
console with the name `<your-controller-name>_request`, with the same
parameters as the ones already there.

If the queue is there and there is a buildup of messages, a likely cause is
that a cloudmaster process died while holding the `/home/lantern/map.lock`.
This could happen if the cloudmaster shuts down as required by unattended
security updates.  To work around this:

- Warn bns-ops about what you're about to do, so nobody steps on each other's
  toes.
- Log into the cloudmaster (`bin/ssh_cloudmaster.py`).
- `cd /home/lantern`
- Temporarily disable the `cloudmaster.py` cron job.  A brutish but effective
  way to do this is `mv cloudmaster.py cloudmaster.bak`.
- Kill all running cloudmaster.py or salt_cloud processes (find them with e.g. `ps aux | grep cloud`).
- `rm map.lock production-cloudmaster-*.*` (replacing
  'production-cloudmaster' with your cloudmaster's host name if necessary).
- Reenable the cloudmaster cron job: `mv cloudmaster.bak cloudmaster.py`
- Let bns-ops know that you're done.
