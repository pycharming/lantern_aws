class ejabberd {
    $ejabberd_package   = 'ejabberd'
    $ejabberd_cfg       = '/etc/ejabberd/ejabberd.cfg'
    $ejabberd_cfg_t     = "${module_name}/ejabberd.cfg"
    $ejabberd_upstart   = '/etc/init/ejabberd.conf' 
    $ejabberd_upstart_t = "${module_name}/upstart.conf"
    $ejabberd_cert      = '/etc/ejabberd/ejabberd.pem'
    $ejabberd_service   = 'ejabberd'

    $xmpp_public_domain  = 'getlantern.org'
    $anonymizer_host     = 'axr.getlantern.org'
    $anonymizer_port     = '8778'
    $anonymizer_password = 'b0yXWXft9yAz6hRJz3kEg9g8A0RVOwjOWRIHBKM+fmw='
    
    package { $ejabberd_package:
        ensure => 'present',
    }

    file { $ejabberd_cfg:
        owner => 'root',
        group => 'ejabberd',
        mode  => '0640',
        content => template($ejabberd_cfg_t),
        require => Package[$ejabberd_package], 
    }
    
    file { $ejabberd_cert: 
      owner   => 'root',
      group   => 'ejabberd',
      mode    => '0640',
      source  => 'puppet:///modules/ejabberd/ejabberd.pem', 
      require => Package[$ejabberd_package],
    }
    
    file { $ejabberd_upstart:
      owner   => 'root',
      group   => 'root',
      mode    => '0644',
      content => template($ejabberd_upstart_t)
    }
  
    # replace ejabberd init script with upstart script
        
    service { 'ejabberd_init_scripts':
      name     => $ejabberd_service,
      ensure   => 'stopped', 
      enable   => 'false',
      provider => 'debian',
      require  => Package[$ejabberd_package],
    }
    
    service { $ejabberd_service:
        ensure    => running,
        provider  => 'upstart',
        subscribe => File[$ejabberd_cfg],
        require   => [ File[$ejabberd_upstart], 
                       File[$ejabberd_cfg], 
                       File[$ejabberd_cert], 
                       Service['ejabberd_init_scripts']],
    }
    
}
