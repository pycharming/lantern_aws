
#
# configures automatic security updates
#
class automatic_updates {
  
  package { "unattended-upgrades":
    ensure => present
  }
  
  file { "/etc/apt/apt.conf.d/10periodic":
    content => template("${module_name}/10periodic"),
    owner => 'root',
    group => 'root',
    mode  => '0600',
    require => Package["unattended-upgrades"]
  }
  
  file { "/etc/apt/apt.conf.d/50unattended-upgrades":
    content => template("${module_name}/50unattended-upgrades"),
    owner => 'root',
    group => 'root',
    mode  => '0600',
    require => Package["unattended-upgrades"] 
  }
  
}