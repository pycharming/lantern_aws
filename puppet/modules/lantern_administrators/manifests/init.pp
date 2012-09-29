
class lantern_administrators {

  lantern_admin { "forkner": 
    ensure => 'present',
    uid    => '4000',
    passwd => '\$6\$jB.rCxf9mWsj\$rGBab/4kec7o4W62qjHpPw.tCzVzGHudr1dacUd16OxucMjkHvIXuHbkhauWnqmr8QtI4QmIoz6Wb8ub9dHwJ0'
  }
  
  lantern_admin { "myles": 
    ensure => 'present',
    uid    => '4001',
  }
  
  lantern_admin { "pants": 
    ensure => 'present',
    uid    => '4002',
  }

  lantern_admin { "aranhoide":
    ensure => 'present',
    uid    => '4003',
  }
  
  # # also nuke the default ubuntu user
  # user { "ubuntu": 
  #   ensure => 'absent'
  # }
  # 
  # file { "/home/ubuntu":
  #   ensure => 'absent'
  # 
  # }
   
}

define lantern_admin($ensure=present, $uid=undef, $passwd=undef) {

  $username      = $name
  $user_home     = "/home/$username"
  $default_shell = '/bin/bash'
  $sudoers_t     = "${module_name}/nopw_sudoers"

  # $masterless::master_user XXX fold in masterless?  
  $gitpuppet_user = "gitpuppet" 
  
  
  group { $username: 
    ensure => present,
    gid    => $uid
  }

  if $ensure == 'present' {
    user { $username:
      ensure => $ensure,
      home   => $user_home,
      uid    => $uid,
      gid    => $username,
      shell  => $default_shell,
      groups => ['adm', 'dialout', 'cdrom', 'floppy', 'audio', 'dip', 'video', 'plugdev', 'netdev', 'admin'],
    }
    
    file { $user_home:
      ensure  => directory,
      owner   => $username,
      mode    => 0700,
      require => User[$username]
    }

    if $passwd {
      # not great, puts hashed pw in process info
      exec { "set passwd $user":
        command => "/bin/echo $username:$passwd | /usr/sbin/chpasswd -e",
        # only if password changed ... 
        onlyif => "/usr/bin/test $passwd != `/bin/egrep ^$username: /etc/shadow | /usr/bin/awk -F: '{print \$2}'`"
      }
    }
  }
  else {
    user { $username: 
      ensure => $ensure
    }
    file { $user_home:
      ensure => $ensure
    }
  }
  
  file { "/etc/sudoers.d/90-$username":
    ensure  => $ensure,
    owner   => 'root', 
    group   => 'root',
    mode    => '0440',
    content => template($sudoers_t),
  }
  
  ssh_authorized_key { "$username login":
    ensure  => $ensure,
    key     => template("${module_name}/$username.pub_key"),
    type    => 'rsa',
    user    => $username,
    require => [ File[$user_home], User[$username] ]
  }
  
  # authorize git configuration push via this key
  ssh_authorized_key { "$username gitpuppet":
    ensure  => $ensure,
    key     => template("${module_name}/$username.pub_key"),
    type    => 'rsa',
    user    => $gitpuppet_user,
  }
  
}
