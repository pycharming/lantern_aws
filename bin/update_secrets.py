#!/usr/bin/env python

import here
import util


def update(key_path, address):
    util.rsync(key_path,
               address,
               local_path=here.secrets_path,
               remote_path='secret')

if __name__ == '__main__':
    util.call_with_key_path_and_address(update)
