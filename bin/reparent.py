import os

import yaml


os.system("mv /home/lantern/minion_master.pub /etc/salt/pki/minion/")
d = yaml.load(file("/etc/salt/minion"))
d['master'] = "<master IP here>"
# You can obtain this by entering a bogus one and checking the error message.
d['master_finger'] = "<master fingerprint here>"
yaml.dump(d, file("/etc/salt/minion", 'w'))
os.system("service salt-minion restart")
print "done!"
