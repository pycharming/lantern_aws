# To copy verbatim.
{% set nontemplate_files=[
    ('/etc/init/', 'broker.conf', 'broker.conf', 'root', 644),
    ('/home/lantern/', 'broker', 'broker', 'lantern', 700),
    ('/etc/', 'rc.local', 'rc.local', 'root', '755')
] %}

include:
    - pubsub_ufw_rules

{% for dir,dst_filename,src_filename,user,mode in nontemplate_files %}
{{ dir+dst_filename }}:
    file.managed:
        - source: salt://pubsub/{{ src_filename }}
        - user: {{ user }}
        - group: {{ user }}
        - mode: {{ mode }}
{% endfor %}

broker-service:
    service.running:
        - name: broker
        - enable: yes
        - require:
            - pkg: tcl
            - cmd: ufw-rules-ready

net.ipv4.tcp_max_syn_backlog:
    sysctl.present:
        - value: 4096

# Update various sysctl settings per the recommendations here -
# https://russ.garrett.co.uk/2009/01/01/linux-kernel-tuning/
net.core.wmem_max:
    sysctl.present:
        - value: 16777216

net.core.rmem_max:
    sysctl.present:
        - value: 16777216

# Note the small minimum buffer size since we primarily process small messages
net.ipv4.tcp_rmem:
    sysctl.present:
        - value: 512 87380 16777216

# Note the small minimum buffer size since we primarily process small messages
net.ipv4.tcp_wmem:
    sysctl.present:
        - value: 512 87380 16777216

net.ipv4.tcp_max_syn_backlog:
    sysctl.present:
        - value: 4096

net.core.netdev_max_backlog:
    sysctl.present:
        - value: 2500

# Increase the current txqueuelen
# This is done permanently in /etc/rc.local
/sbin/ifconfig eth0 txqueuelen 20000:
    cmd.run
