# Lantern Cloud

This project contains code and configuration scripts to launch and manage cloud-hosted infrastructure for the [Lantern](https://github.com/getlantern/lantern) censorship circumvention tool.

At this moment, three types of machines are launched and managed by this project:

- **Chained Proxies**: These offer access to the free internet to Lantern users.

- **Cloudmasters**, which launches fallback proxies, runs checks on them, and allows to run batch jobs in them (in particular, updating their configuration).

## How does it work

Cloudmasters listen for requests to launch, retire, an destroy proxies in a reliable redis queue.  Upon serving them, and when necessary, they push their results (e.g., proxy configurations) to redis queues.  Currently, the main system interacting with the cloudmasters in this way is the config server.

[Salt](http://saltstack.com/) is used for configuration management.  The `salt` directory in this project contains the configuration for all the machines (you can see which modules apply to which machines in `salt/top.sls`).  The Cloud Master doubles as a Salt Master for launched peers, so they fetch their configuration from it.

## Usage

### Before you start

Install required packages to run the script that launches cloud masters and other util scripts.

    sudo pip install -U -r requirements.txt

Or if you want to run it in isolated environment:

    virtualenv venv
    . venv/bin/activate
    pip install -U -r requirements.txt

After you check out this repository, and unless you passed the `--recursive` flag to `git clone`, you need to run the following to fetch secrets required by Lantern:

    git submodule update --init

Note that this downloads a private repository that is only accessible to the Lantern core development team.

### Updating the salt configuration of a cloudmaster

Whether you want to change the configuration of the cloudmaster itself or the machines it manages, the first step is syncing the cloudmaster's Salt configuration with your local one.  To do this, run

    bin/update.py

The values in `config.py` will be used to find the Cloud Master to update.

If you want to deploy to a test cloudmaster or proxy, use a `config_overrides.py` (see the section on "Launching a cloudmaster" below).

To update the Salt configuration of all production cloudmasters at once, make sure you have a clean checkout of the latest master and run:

    bin/inallcms bin/update.py

#### Applying the updated configuration

Note that `bin/update.py` doesn't apply the changes to the machines managed by Salt.  Sometimes you only want to upload your salt config in order to update the chained proxies (or even one particular proxy), or only the cloud master, or all of them.

You apply the new configuration by using regular salt commands.  As a convenience, a `bin/ssh_cloudmaster.py [<command>]` script will find your cloud master and run the command you provide there, or just log you in as the root user if you provide no commands.

So, for example, to sync the cloudmaster only to the current configuration:

    bin/ssh_cloudmaster.py 'sudo salt-call state.highstate'

or, as a shortcut,

    bin/hscloudmaster.bash

or, if you want to do this in all production cloudmasters in parallel,

    bin/inallcms bin/hscloudmaster.bash

If you are not sure whether a configuration change requires applying the
changes in the cloudmaster itself, it can't hurt to just do it to be in the safe side.

All chained proxies have salt IDs starting with 'fp-' (fp stands for "fallback proxy", an old name for these), so you can instruct the proxies, but not the cloud master, to apply the current configuration with

    bin/ssh_cloudmaster.py 'salt -b 100 "fp-*" state.highstate'

If you have many proxies in a clodumaster, they may have trouble updating all at once, since they all need to pull files from the master and other servers, and report progress to the master.  `-b 100` makes sure that at most 100 proxies are updated at once.

To do this in the proxies managed by all production cloudmasters,

    bin/inallcms bin/ssh_cloudmaster.py 'salt -b 100 "fp-*" state.highstate'
    
This operation is not 100% reliable, so after running an important update you may need to verify that the update was performed in all machines.  How to do this is explained below, in the "Verify deployment" subsection.

To run an arbitrary command (as root) in all chained proxies:

    bin/ssh_cloudmaster.py 'salt --out=yaml "fp-*" cmd.run "ls /home/lantern/"'

`--out=yaml` ensures that the output is valid YAML and is only needed if you are going to consume the output of this programmaticaly.


#### Common tasks

Tasks will be added here in a per need basis.  You may want to check out the `bin` folder for example scripts.

##### Verify deployment

There is not a general command to verify that all proxies have been updated correctly.  Even if all salt updates have been successful, some bad side effects may have happen.  For example, the `http-proxy` service may fail to restart.

Verifying a deployment is currently a semi-manual process that needs to be performed in each cloudmaster separately.  It goes like this:

First, find a command that will produce all the output you need to verify that your update has been performed in a proxy.  For example, when deploying a new `http-proxy` version we want to make sure that the binary on disk is the new one, and that `http-proxy` successfully started up again after the deployment.  Since there are two things to check, it's OK to use two commands, like so:

    shasum /home/lantern/http-proxy ; service http-proxy status

You may want to verify in a random proxy that this command works.

Next, log into the cloudmaster as root (e.g., with `sudo su`) and apply your command to all proxies and collect the results, like so:

    salt --out=yaml "fp-*" cmd.run "shasum /home/lantern/http-proxy ; service http-proxy status" | tee result

All the parts of the above command are introduced in the "Applying the updated configuration" section above.

To verify the output, call `check_deployment.py`.  It should show you a sample of the outputs and ask you to choose the one you expect.  If this doesn't happen, run `rm expected` and try again.

This script prints out how many proxies produced good vs bad output.  It also saves the erroring proxies to a file called `bad`.  So you can try reapplying Salt state with

    salt -b 100 -L $(cat bad) state.highstate
    salt --out=yaml -L $(cat bad) cmd.run "shasum /home/lantern/http-proxy ; service http-proxy status" | tee result

Then run `check_deployment.py` again.  This time around, it won't ask you for the expected result (it saved that to `expected` last time) and it will print out the new report.

As soon as no bad results are reported, run `rm expected` to clean up and you're done.

###### Common problems

Sometimes a proxy will refuse to apply state.highstate because there's already a running process doing that.  You could wait for that to end, but sometimes that won't happen for a very long time.  It's quicker to just kill the process.  You can use [`kill_running_highstates.py`](https://github.com/getlantern/lantern_aws/blob/master/salt/cloudmaster/kill_running_highstates.py) for that.

Sometimes proxies will reply with `Minion did not return. [not connected]`.  Most often, these are machines that are being launched.  These may have the new or old configurations applied.  You may want to check on these later.  Sometimes cloudmasters will fail to delete the keys of proxies after they're destroyed.  If the date in the name of the erroring proxy is not today, then this is most probably the case.  You may check in the Vultr or Digital Ocean page whether such a proxy exists.  If there's no such proxy, you can delete the key at the cloudmaster with `salt-key -d the-proxy-name`, so you won't get these again.  Otherwise, and if you're unsure what to do, ask in the dev channel or mailing list.

##### Perform basic checks on newly launched minions

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

and making sure that new stuff keeps getting printed.  If that's not the case, you may need to kill the process with the given PID in the proxy so Salt will let you try and reapply the config.

The following will check for a running HTTP proxy:

    bin/ssh_cloudmaster.py 'salt "fp-*" cmd.run "service http-proxy status"' | tee status

If all you want to know is whether the machine(s) are done setting themselves
up (e.g., you haven't made any config changes), you can run something like
(e.g., for flashlight servers)

    bin/ssh_cloudmaster.py 'salt "fl-20150327-*" cmd.run "service http-proxy status"'

If you expect to run a lot of these it will be faster log into the
cloudmaster (just 'bin/ssh_cloudmaster.py` without arguments) and run the
commands from there.

#### Less common tasks

##### Launching a cloud master

Currently this is a manual process.

 - Launch a VPS of the size you want in the provider and datacenter you want (2GB is currently recommended for production ones).  Some considerations:
   - The name must follow the convention `cm-<datacenter><optionalextrastuff>`.  For example, if want to launch a test cloudmaster for yourself in the `donyc3` datacenter, call it `cm-donyc3myname`.  A production cloudmaster must not have any extra stuff attached to its name (for example, the production cloudmaster for that datacenter is just `cm-donyc3`).
   - Remember to provide your own SSH key in addition to the cloudmaster ones.
   - Although these are not currently being used, selecting the options for IPv6 support and private networking might be a good idea for forward compatibility.
 - ssh into `root@<your-new-cloudmaster-ip>` and run:

```bash
NAME="<your-cloudmaster's-name>"
mkdir -p /srv/pillar
touch /srv/pillar/$NAME.sls
curl -L https://bootstrap.saltstack.com | sh -s -- -M -A 127.0.0.1 -i $NAME git v2015.5.5
salt-key -ya $NAME
```
 - in your own computer, make a new file with contents similar to these:

```
cloudmaster_name = "cm-donyc3myname"
cloudmaster_address = "188.166.40.244"
```

- and place it in `~/git/lantern_aws/bin/config_overrides.py`.  You probably want to have it saved somewhere else too, since you'll be deleting and restoring `config_overrides.py` to alternate between the production deployment and one or more non-production ones.
- `cd ~/git/lantern_aws/bin`
- `./update.py && ./hscloudmaster.bash`

Your cloudmaster should be ready now.  If it's not a production one (XXX: add instructions for making it a production one) it will be running against a local redis DB.
