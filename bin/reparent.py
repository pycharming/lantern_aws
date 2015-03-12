import os

import yaml


os.system("mv /home/lantern/minion_master.pub /etc/salt/pki/minion/")
d = yaml.load(file("/etc/salt/minion"))
d['master'] = "PUT DESTINATION CLOUDMASTER IP HERE"
d['master_finger'] = ""
yaml.dump(d, file("/etc/salt/minion", 'w'))
os.system("service salt-minion restart")
print "done!"
