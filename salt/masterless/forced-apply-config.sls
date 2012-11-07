#!py

def run():

    import random
    import socket

    random.seed(socket.gethostname())
    minute = random.randint(0, 59)

    return {"/root/apply-config.sh --force":
               {'cron':
                   ['present',
                    {'minute': minute},
                    {'require':
                        [{'file': '/root/apply-config.sh'}]}]}}
