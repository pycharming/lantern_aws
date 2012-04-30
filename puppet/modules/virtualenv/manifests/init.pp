define virtualenv($requirements=undef, $owner=undef, $group=undef) {

  $root = $name

  file { $root:
    ensure  => directory, 
    owner   => $owner,
    group   => $group,
  }

  Exec {
    user  => $owner, 
    group => $group,
    cwd   => '/tmp'
  }
  
  exec { "virtualenv $root":
    command => "/usr/bin/virtualenv $root",
    creates => "$root/bin",
    notify  => Exec["update tools in $root"],
    require => [File[$root], Package["python-virtualenv"], ],
  }

  exec { "update tools in $root":
    command     => "$root/bin/pip install -U distribute pip",
    refreshonly => true
  }
  
  if $requirements {
    pip::requirements { $requirements: 
      venv   => $root,
      owner  => $owner,
      group  => $group,
      require => [ File[$requirements], Exec["update tools in $root"], ],
    }
  }
      
  package { "python-virtualenv":
    ensure => 'present'
  }

  package { "python-pip": 
    ensure => 'present'
  }

}

define pip::requirements($venv, $owner=undef, $group=undef) {
  $requirements = $name
  
  exec { "update requirements $name in $venv":
    command     => "$venv/bin/pip install -r $requirements",
    cwd         => '/tmp',
    user        => $owner,
    group       => $group, 
    subscribe   => File[$requirements],
  }

}