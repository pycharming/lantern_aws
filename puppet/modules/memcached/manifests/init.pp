class memcached {
    $memcached_package      = "memcached"
    $memcached_conf         = "/etc/memcached.conf"
    $memcached_conf_t       = "${module_name}/memcached.conf" 
    $memcached_service      = "memcached"
    $memcached_init_scripts = "memcached_init_scripts"
    $memcached_upstart      = "/etc/init/memcached.conf"
    $memcached_upstart_t    = "${module_name}/upstart.conf"
 
    package { $memcached_package:
        ensure => 'present',
    }
 
    file { $memcached_conf:
        owner => 'root',
        group => 'root',
        mode  => '0644',
        content => template($memcached_conf_t),
        require => Package[$memcached_package],
    }

    # replace memcached init scripts with upstart scripts

    file { $memcached_upstart:
      owner   => 'root',
      group   => 'root',
      mode    => '0644',
      content => template($memcached_upstart_t)
    }

    service { $memcached_init_scripts: 
      name     => $memcached_service,
      ensure   => 'stopped',
      enable   => false,
      provider => 'debian',
      require  => Package[$memcached_package],
    }

    service { $memcached_service:
        ensure    => running,
        provider  => 'upstart', 
        subscribe => File[$memcached_conf],
        require   => [ File[$memcached_conf], 
                       File[$memcached_upstart], 
                       Service[$memcached_init_scripts], ],
    }

}
