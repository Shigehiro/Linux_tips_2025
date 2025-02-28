#!/usr/bin/env python3

"""
Add or delete a BGP path by modifying the frr.service config based on the result of a DNS health check.
"""

import time
import os
import sys
import argparse
import dns.message
import dns.query
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--anycast_ip', type=str, required=True, help='Specify an Anycast IP')
parser.add_argument('-as', '--as_number', type=int, required=True, help='Specify a BGP AS number')
args = parser.parse_args()
anycast_ip = args.anycast_ip
as_number = args.as_number

def del_bgp_path():
    vtysh_cmd = '/usr/bin/vtysh -f /tmp/vtysh.conf'

    command_text = f"""
    router bgp {as_number}
    address-family ipv4 unicast
    no network {anycast_ip}/32
    exit
    exit
    exit
    write memory
    exit
    """

    with open('/tmp/vtysh.conf', 'w') as f:
        f.write(command_text)
    subprocess.run(vtysh_cmd.split(), stdout=subprocess.PIPE, stderr = subprocess.PIPE)

def check_process_staus(name):
    command = f"systemctl is-active {name}"
    stdout = subprocess.run(command.split(), capture_output=True, text=True).stdout
    if 'active' == stdout.lower().rstrip():
        return True
    else:
        return False

def post_setup():
    counter = 0
    if counter < 5:
        if check_process_staus(name='frr.service') and counter < 3:
            del_bgp_path()
            sys.exit()
        elif counter < 5:
            counter += 1
            time.sleep(1)
        elif counter > 5:
            sys.exit()

if __name__ == '__main__':
    post_setup()
