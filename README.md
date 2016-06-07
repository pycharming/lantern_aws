NOTE - this repo manages large files using [git lfs](https://git-lfs.github.com/).
Please install the git lfs client in order to use this repo. Also make sure to
run `git lfs install` once in order to install the global git-lfs hooks for git.

# Lantern Cloud

This project contains code and configuration scripts to launch and manage cloud-hosted infrastructure for the [Lantern](https://github.com/getlantern/lantern) censorship circumvention tool.

At this moment, three types of machines are launched and managed by this project:

- **Chained Proxies**: These offer access to the free internet to Lantern users.

- **Cloudmasters**, which launches fallback proxies, runs checks on them, and allows to run batch jobs in them (in particular, updating their configuration).

## How does it work
Cloudmasters listen for requests to launch, retire, an destroy proxies in a reliable redis queue.  Upon serving them, and when necessary, they push their results (e.g., proxy configurations) to redis queues.  Currently, the main system interacting with the cloudmasters in this way is the config server.

[Salt](http://saltstack.com/) is used for configuration management.  The `salt` directory in this project contains the configuration for all the machines (you can see which modules apply to which machines in `salt/top.sls`).  The Cloud Master doubles as a Salt Master for launched peers, so they fetch their configuration from it.

### Where do servers get their binaries
Binaries for things like our http-proxy and config servers are stored and
versioned directly within this lantern_aws repo using git lfs. Binaries are
hosted on the Cloudmasters and distributed from there to the servers that need
them. 

## How can I test this stuff?
For small local changes, you can launch your own Cloudmaster per the
instructions below, launch your own servers from that Cloudmaster and deploy
uncommitted code directly to your test environment.

### Staging
The whole team shares a staging environment with its own set of Cloudmasters
like `cm-donyc3staging`. For bigger changes, it's a good idea to deploy those
to staging first.  To do that, simply merge your configuration changes into
the [staging branch](https://github.com/getlantern/lantern_aws/tree/staging)
and also add any preview builds of your binaries to this branch. Then, deploy
from that branch using the usual `bin/update.py` script.

### Redis
Production and staging both have a pair of Redis servers. At any given time,
only one member of each pair is acting as the master that serves requests
from clients, while the other acts as a read-only slave replica.

#### Production Redis

* redis-donyc3-001 - Currently master
* redis-donyc2-002 - Currently slave

#### Staging Redis

* redis-donyc3staging-001 - Currently master
* redis-donyc3staging-002 - Currently slave

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

You apply the new configuration by using regular salt commands.  As a convenience, a `bin/ssh_cloudmaster.py [<command>]` script will find your cloud master and run the command you provide there, or just log you in if you provide no commands.  Note that although you have passwordless sudo, you're logged in as yourself and not as `root`, so if you intend to run any command with superuser privileges you need to prepend `sudo ` to it.

So, for example, to sync the cloudmaster only to the current configuration:

    bin/ssh_cloudmaster.py 'sudo salt-call state.highstate'

or, as a shortcut,

    bin/hscloudmaster.bash

or, if you want to do this in all production cloudmasters in parallel,

    bin/inallcms bin/hscloudmaster.bash

If you are not sure whether a configuration change requires applying the
changes in the cloudmaster itself, it can't hurt to just do it to be in the safe side.

All chained proxies have salt IDs starting with 'fp-' (fp stands for "fallback proxy", an old name for these), so you can instruct the proxies, but not the cloud master, to apply the current configuration with

    bin/ssh_cloudmaster.py 'sudo salt -b 100 "fp-*" state.highstate'

If you have many proxies in a cloudmaster, they may have trouble updating all at once, since they all need to pull files from the master and other servers, and report progress to the master.  `-b 100` makes sure that at most 100 proxies are updated at once.

To do this in the proxies managed by all production cloudmasters,

    bin/inallcms bin/ssh_cloudmaster.py 'sudo salt -b 100 "fp-*" state.highstate'

This operation is not 100% reliable, so after running an important update you may need to verify that the update was performed in all machines.  How to do this is explained below, in the "Verify deployment" subsection.

To run an arbitrary command (as root) in all chained proxies:

    bin/ssh_cloudmaster.py 'sudo salt --out=yaml "fp-*" cmd.run "ls /home/lantern/"'

`--out=yaml` ensures that the output is valid YAML and is only needed if you are going to consume the output of this programmaticaly.


#### Common tasks

Tasks will be added here in a per need basis.  You may want to check out the `bin` folder for example scripts.

##### Verify deployment

There is not a general command to verify that all proxies have been updated correctly.  Even if all salt updates have been successful, some bad side effects may have happened.  For example, the `http-proxy` service may have failed to restart.

Verifying a deployment is currently a semi-manual process that needs to be performed in each cloudmaster separately.  It goes like this:

First, find a command that will produce all the output you need to verify that your update has been performed in a proxy.  For example, when deploying a new `http-proxy` version we want to make sure that the binary on disk is the new one, and that `http-proxy` successfully started up again after the deployment.  Since there are two things to check, it's OK to use two commands, like so:

    shasum /home/lantern/http-proxy ; service http-proxy status

You may want to verify in a random proxy that this command works.

Next, log into the cloudmaster as root (e.g., with `sudo su`) and apply your command to all proxies and collect the results, like so:

    salt --out=yaml "fp-*" cmd.run "shasum /home/lantern/http-proxy ; service http-proxy status | cut -d ' ' -f 2" | tee result

All the parts of the above command are introduced in the "Applying the updated configuration" section above, except the `| cut -d ' ' -f 2` one.  On success, `service http-proxy status` prints out the PID of the `http-proxy` process, which will generally be different for each proxy.  We only care about whether the proxy is running or not, and as we'll see, we want the output to be the same for all successful proxies, so we use `cut` to ignore everything but the second word (which we expect to be `start/running`) in the output of that command.

To verify the output, call `check_deployment.py`.  It should show you a sample of the outputs and ask you to choose the one you expect.  If this doesn't happen, run `rm expected` and try again.

This script prints out how many proxies produced good vs bad output.  It also saves the erroring proxies to a file called `bad`.  So you can try reapplying Salt state with

    salt -b 100 -L $(cat bad) state.highstate
    salt --out=yaml -L $(cat bad) cmd.run "shasum /home/lantern/http-proxy ; service http-proxy status" | tee result

Then run `check_deployment.py` again.  This time around, it won't ask you for the expected result (it saved that to `expected` last time) and it will print out the new report.

As soon as no bad results are reported, run `rm expected` to clean up and you're done.

###### Common problems

Sometimes a proxy will refuse to apply state.highstate because there's already a running process doing that.  You could wait for that to end, but sometimes that won't happen for a very long time.  It's quicker to just kill the process.  You can use [`kill_running_highstates.py`](https://github.com/getlantern/lantern_aws/blob/master/salt/cloudmaster/kill_running_highstates.py) for that.

Sometimes proxies will reply with `Minion did not return. [Not connected]`.  Most often, these are machines that are being launched.  These may have the new or old configurations applied.  You may want to check on these later.  Sometimes cloudmasters will fail to delete the keys of proxies after they're destroyed.  If the date in the name of the erroring proxy is not today, then this is most probably the case.  You may check in the Vultr or Digital Ocean page whether such a proxy exists.  If there's no such proxy, you can delete the key at the cloudmaster with `salt-key -d the-proxy-name`, so you won't get these again.  Otherwise, and if you're unsure what to do, ask in the dev channel or mailing list.

If, on the other hand, you see proxies replying with `Minion did not return. [No response]`, this may well be a failure when checking, so you can just run the check command again on those (or, more conveniently, on `-L $(cat bad)`) without running highstate again on them, and you'll often get a proper response from these.

In cloudmasters with many proxies, it's not uncommon to get something like this:

```
Executing run on ['fp-https-vltok1-20160428-210', 'fp-https-vltok1-20160407-234', 'fp-https-vltok1-20160424-160', 'fp-https-vltok1-20160424-163', 'fp-https-vltok1-20160407-237', 'fp-https-vltok1-20160407-230', 'fp-https-vltok1-20160407-231', 'fp-https-vltok1-20160407-232', 'fp-https-vltok1-20160407-233', 'fp-https-vltok1-20160424-169', 'fp-https-vltok1-20160424-168']

Traceback (most recent call last):
  File "/usr/bin/salt", line 10, in <module>
    salt_main()
  File "/usr/lib/python2.7/dist-packages/salt/scripts.py", line 349, in salt_main
    client.run()
  File "/usr/lib/python2.7/dist-packages/salt/cli/salt.py", line 103, in run
    for res in batch.run():
  File "/usr/lib/python2.7/dist-packages/salt/cli/batch.py", line 155, in run
    part = next(queue)
  File "/usr/lib/python2.7/dist-packages/salt/client/__init__.py", line 714, in cmd_iter_no_block
    **kwargs):
  File "/usr/lib/python2.7/dist-packages/salt/client/__init__.py", line 934, in get_iter_returns
    jinfo = self.gather_job_info(jid, tgt, tgt_type)
  File "/usr/lib/python2.7/dist-packages/salt/client/__init__.py", line 202, in gather_job_info
    timeout=timeout,
  File "/usr/lib/python2.7/dist-packages/salt/client/__init__.py", line 290, in run_job
    raise SaltClientError(general_exception)
salt.exceptions.SaltClientError: Salt request timed out. The master is not responding. If this error persists after verifying the master is up, worker_threads may need to be increased.
```

This might be a sign that we need a bigger cloudmaster for this datacenter.  It's also possible that you've been unlucky and your update run at the same time as some resource-intensive test.

Either way, you just need to keep running the update/verify procedure (perhaps with a lower `-b` argument).  The proxies that failed to update themselves this run will be retried in the next iteration.  Proxies that have already updated themselves will not need be retried, so the cloudmaster will be a little less burdened each iteration.

##### Perform basic checks on newly launched minions

Once you have launched a minion by any of the methods described below, the
machine will start applying the Salt configuration on its own.  A common
problem when first testing configuration changes is that Salt rejects your .sls
files altogether (for example, if you have some YAML or Jinja syntax error).
One way to quickly detect that is to run

    bin/ssh_cloudmaster.py 'sudo salt <your-machine-id> state.highstate'

If your .sls files have errors, the output of this command will make that
clear.  If, on the contrary, you get something like this:

    fp-test-001:
        Data failed to compile:
    ----------
        The function "state.highstate" is running as PID 4120 and was started at  with jid req

then at least the syntax seems OK.  If you have nothing better to do, you can make sure progress is being made by periodically running:

    bin/ssh_cloudmaster.py 'sudo salt <your-machine-id> cmd.run 'tail -n 40 /var/log/salt/minion'

and making sure that new stuff keeps getting printed.  If that's not the case, you may need to kill the process with the given PID in the proxy so Salt will let you try and reapply the config.

The following will check for a running HTTP proxy:

    bin/ssh_cloudmaster.py 'sudo salt "fp-*" cmd.run "service http-proxy status"' | tee status

If you expect to run a lot of these it will be faster log into the
cloudmaster (just 'bin/ssh_cloudmaster.py` without arguments) and run the
commands from there.

#### Less common tasks

##### Launching a cloud master

[XXX: updating these instructions for Linode is pending, because I'm still figuring out how to make it more like the others.  For the time being, some known differences:

- Linode Ubuntu 14.04 machines don't come with `curl` installed.  `apt-get install curl` before trying to install Salt should fix this.

- In Linode you need to set a default root password.  This doesn't play well with `update.py`, and password login will get disabled the first time you run Salt highstate.  Therefore, after having launched your cloudmaster, you need to upload your SSH key there (e.g. `ssh-copy-id root@<your cloudmaster's IP>`) before running `update.py`.

- I don't yet know whether private networking and/or IPv6 need to be explicitly enabled.

/XXX]

Currently this is a manual process.

 - Launch a VPS of the size you want in the provider and datacenter you want (2GB is currently recommended for production ones).  Some considerations:
   - The name must follow the convention `cm-<datacenter><optionalextrastuff>`.  For example, if want to launch a test cloudmaster for yourself in the `donyc3` datacenter, call it `cm-donyc3myname`.  A production cloudmaster must not have any extra stuff attached to its name (for example, the production cloudmaster for that datacenter is just `cm-donyc3`).
   - Remember to provide your own SSH key in addition to the cloudmaster ones.
   - Although these are not currently being used, selecting the options for IPv6 support and private networking might be a good idea for forward compatibility.
 - ssh into `root@<your-new-cloudmaster-ip>` and run [1]:

```bash
NAME="<your-cloudmaster's-name>"
mkdir -p /srv/pillar
touch /srv/pillar/$NAME.sls
curl -L https://bootstrap.saltstack.com | sh -s -- -M -A 127.0.0.1 -i $NAME git v2015.8.8.2
salt-key -ya $NAME
salt-cloud -u
```
 - in your own computer, make a new file with contents similar to these:

```
cloudmaster_name = "cm-donyc3myname"
cloudmaster_address = "188.166.40.244" # Must use IP address here. Lots of pillars depend on an correct IP address.
```

- and place it in `~/git/lantern_aws/bin/config_overrides.py`.  You probably want to have it saved somewhere else too, since you'll be deleting and restoring `config_overrides.py` to alternate between the production deployment and one or more non-production ones.
- `cd ~/git/lantern_aws/bin`
- `./update.py --as-root` (you only need to run --as-root until you've successfully run state.highstate once)
- back in the cloudmaster [2]:
- `salt-call state.highstate | tee hslog`
- `python -c "import redis_util; redis_util.redis_shell.set('sshalert-whitelist:<MY-IP>', '<MY-USER>')"`

Remember to change <MY-IP> to your public IP and <MY-USER> to your login user.

Your cloudmaster should be ready now.  If it's not a production one (XXX: add instructions for making it a production one) it will be running against a local redis DB.

[1] Please double-check in [bin/config.py](https://github.com/getlantern/lantern_aws/blob/master/bin/config.py) that this version is current.  Also, the `salt-cloud -u` line is only required due to a bug in `v2015.8.8.2`.

[2] You can't use `bin/hscloudmaster.bash` here because it hasn't been adapted to work as root, which is only needed during this bootstrap procedure.

##### Launching a proxy

First, add an request to the queue.
```python
from redis_util import redis_shell as r
r.lrange('donyc3myname:srvreqq', 0, -1) # should only have the sentinel value: [-1]
# if the result of above command is [], append the sentinel manually
r.lpush('donyc3myname:srvreqq', -1)

# only below command is absolutely required
r.lpush('donyc3myname:srvreqq', 1) # can be any positive number not already there
```

The `refill_srvq` service should already be running on the cloudmaster. You just need to monitor the progress:

```
tail -f /var/log/syslog | grep refill
```

If something wrong executing the service, you can also run the refill process manually.
```sh
MAXPROCS=1 QSCOPE=CM refill_srvq.py
```

The script runs forever. After you see output similar to below, halt the script.
```
Serving queue donyc3myname:srvreqq , MAXPROCS: 1
Got request 1
Starting process to launch fp-https-donyc3myname-20160606-001
...
VPS up!
...
```

##### Launching a redis server
For replication purposes, Redis servers can be either masters or slaves.  At any
one time, there should be only one master, and DNS should be configured so that
redis.getlantern.org resolves to the master.

The only difference between masters and slaves is that masters have the pillar
`is_redis_master: "True"`.

To launch a redis server named `redis-donyc3-001` in the `donyc3` datacenter:

On the cloudmaster `cm-donyc3`:

```
sudo touch /srv/pillar/redis-donyc3-001.sls
# If you want this to be a redis master
sudo /bin/sh -exec "echo 'is_redis_master: \"True\"' > /srv/pillar/redis-donyc3-001.sls"
sudo salt-cloud -p donyc3_4GB redis-donyc3-001
sudo salt "redis-donyc3-001" state.highstate
```

The first time you run highstate, redis may fail to install. To resolve this,
ssh to the machine as lantern and then run the following:

```
ssh lantern@<ip>
sudo rm /var/lib/dpkg/lock
sudo dpkg --configure -a
sudo apt-get install redis-server=3:3.0.7-1chl1~trusty1
sudo rm /var/cache/salt/minion/proc/*
```

After this point, run `state.highstate` again and it should run successfully
from here on out. The machine may still be running a Redis instance started by
the old init.d script. You can fix this by rebooting the machine.

##### Upgrading a cloudmaster's Salt version

This procedure is for upgrading to v2015.8.8.2.  It isn't guaranteed to work with every version, but it should be a good baseline.

- ssh into your cloudmaster.

- upgrade all minions.  Just copying and pasting this command should work:

```
salt -C 'not E@cm-' cmd.run 'curl -L https://bootstrap.saltstack.com | sh -s -- -A $(salt-call grains.get master | tail -n 1 | tr -d "[[:space:]]") -i $(salt-call grains.get id | tail -n 1 | tr -d "[[:space:]]") git v2015.8.8.2'
```
- upgrade the master itself (**NOTE: it's important to upgrade the minions before**), running a similar command locally:

```
curl -L https://bootstrap.saltstack.com | sh -s -- -M -A 127.0.0.1 -i $(salt-call grains.get id | tail -n 1 | tr -d "[[:space:]]") git v2015.8.8.2
```

### Caveats

This is a list of known fragile points to consider before making changes, or if something breaks for no apparent cause.

- `linode_util.all_vpss` kind of assumes that linode VPSs only have one public IP address.  If more than one is available, an arbitrary one will be listed, and a warning will be printed out to stderr.
