#
# this module sets up a masterless puppet
# configuration operated via git.
#
# when the repo is pushed to, puppet configuration 
# is replaced and a cron job eventually picks up 
# the changes.
#

class masterless {

  $git_package         = 'git'
  $cron_package        = 'cron'
  $master_user         = 'gitpuppet'
  $master_home         = "/home/$master_user"
  $puppet_group        = 'puppet'
  $repo_dir            = "$master_home/configure"
  $apply_config_script = "/root/apply-config.sh"
  $puppet_config_dir   = "/etc/puppet"

  package { $git_package:
    ensure => 'present'
  }

  package { $cron_package: 
    ensure => 'present'
  }

  #
  # the master user controls the git repository 
  # that the puppet configuration is stored in.
  #
  user { $master_user:
    ensure  => 'present',
    home    => "$master_home",
    gid     => "$puppet_group",
    shell   => '/usr/bin/git-shell',
    require => Package[$git_package],
  }

  file { $master_home:
    ensure  => directory,
    owner   => $master_user,
    mode    => '0700',
    require => User[$master_user],
  }

  #
  # this is the public key that is authorized to 
  # push to the puppet configuration repository. 
  #
  # the key data must be placed in the file 
  # referenced by key before executing.
  #
  # Not Doing this here, using separate administrative
  # configuration.
  # 
  # ssh_authorized_key { $master_user:
  #   ensure  => present,
  #   key     => template("${module_name}/id_rsa.pub_key"),
  #   name    => "git@localhost",
  #   type    => rsa,
  #   require => File[$master_home],
  #   user    => $master_user,
  # }

  #
  # the master user owns the main puppet 
  # configuration directory so it can overwrite
  # it when the configuration repo changes.
  #
  # the puppet group is given read access so that
  # puppet itself can get to the current config.
  #
  file { $puppet_config_dir: 
    ensure  => directory, 
    owner   => $master_user,
    group   => $puppet_group,
    mode    => '0750'
  }

  #
  # this is where the puppet configuration repo 
  # is stored. 
  #
  file { $repo_dir:
    ensure  => directory,
    owner   => $master_user,
    mode    => '0700',
    require => File[$master_home]
  }

  # 
  # init the repo
  #
  exec { "Create puppet Git repo":
    alias   => 'create-repo',
    cwd     => $repo_dir,
    user    => $master_user,
    command => "/usr/bin/git init --bare",
    creates => "$repo_dir/hooks",
    require => [File[$repo_dir], Package[$git_package], User[$master_user]],
  }

  #
  # this hook executes when the repo is updated, 
  # its job is to export the current state of 
  # the repository into the puppet configuration
  # folder and mark it as needing an update.
  #
  file { "$repo_dir/hooks/post-receive":
    ensure  => present,
    owner   => $master_user,
    mode    => '0700',
    require => Exec['create-repo'],
    content => template("${module_name}/post-receive"),
  }
  
  #
  # this script is run periodically to check for 
  # changes in the configuration.
  #
  file { $apply_config_script:
    ensure  => present,
    owner   => 'root',
    mode    => '0700',
    content => template("${module_name}/apply-config.sh"),
  }

  #
  # this cron job runs frequently to pick up 
  # any changes in the local config.  It will
  # only execute puppet if the configuration is 
  # marked as 'dirty' by a git push. 
  #
  # this makes it light weight but unable to 
  # fix intermittent errors due to network 
  # conditions or external servers. Another 
  # job runs puppet in full on a slower cycle
  # unconditionally.
  #
  cron { "puppet-apply-if-dirty":
    ensure  => present,
    command => $apply_config_script,
    user    => 'root',
    minute  => '*',
    require => File[$apply_config_script],
  }
  
  #
  # this cron job runs once an hour and 
  # always runs puppet to check the 
  # configuration.
  #
  # the application occurs at a 'random' 
  # minute based on the fqdn of the machine
  # so that all nodes do not update at 
  # once and create undue pressure on any 
  # commonly accessed resource.
  #
  cron { "puppet-apply-force": 
    ensure  => present,
    command => "$apply_config_script --force",
    user    => 'root',
    minute  => fqdn_rand(60),
    require => File[$apply_config_script],
  }

}
