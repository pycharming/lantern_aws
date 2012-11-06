#!/usr/bin/env python

import random
import socket


random.seed(socket.gethostname())
print random.randint(0, 59)
