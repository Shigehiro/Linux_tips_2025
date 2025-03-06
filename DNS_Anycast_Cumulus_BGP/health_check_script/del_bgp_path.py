#!/usr/bin/env python3

"""
Add or delete a BGP path by modifying the frr.service config based on the result of a DNS health check.
"""

import time
import sys
import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--anycast_ip', type=str, required=True, help='Specify an Anycast IPs, separated with ,')
parser.add_argument('-as', '--as_number', type=int, required=True, help='Specify a BGP AS number')
args = parser.parse_args()
anycast_ip = args.anycast_ip.split(',')
as_number = args.as_number

def make_anycast_ip_list():
    ipv4_list = list()
    ipv6_list = list()
    anycast_ip_list = dict()
    for ip in anycast_ip:
        if '.' in ip:
            ipv4_list.append(ip)
        elif ':' in ip:
            ipv6_list.append(ip)
    anycast_ip_list['ipv4'] = ipv4_list
    anycast_ip_list['ipv6'] = ipv6_list
    return anycast_ip_list

def del_bgp_path_v4_v6(anycast_ip_list):
    for address_family, address_list in anycast_ip_list.items():
        if address_family == 'ipv4':
            for ip in address_list:
                update_route_vtysh_v4(ip=ip, as_number=as_number)
        elif address_family == 'ipv6':
            for ip in address_list:
                update_route_vtysh_v6(ip=ip, as_number=as_number)

def update_route_vtysh_v4(ip, as_number):
    vtysh_cmd = '/usr/bin/vtysh -f /tmp/vtysh_v4.conf'

    command_text = f"""
    router bgp {as_number}
    address-family ipv4 unicast
    no network {ip}/32
    exit
    exit
    exit
    write memory
    exit
    """

    with open('/tmp/vtysh_v4.conf', 'w') as f:
        f.write(command_text)
    subprocess.run(vtysh_cmd.split(), stdout=subprocess.PIPE, stderr = subprocess.PIPE)

def update_route_vtysh_v6(ip, as_number):
    vtysh_cmd = '/usr/bin/vtysh -f /tmp/vtysh_v6.conf'

    command_text = f"""
    router bgp {as_number}
    address-family ipv6 unicast
    no network {ip}/128
    exit
    exit
    exit
    write memory
    exit
    """

    with open('/tmp/vtysh_v6.conf', 'w') as f:
        f.write(command_text)
    subprocess.run(vtysh_cmd.split(), stdout=subprocess.PIPE, stderr = subprocess.PIPE)

def check_process_status(name):
    command = f"systemctl is-active {name}"
    stdout = subprocess.run(command.split(), capture_output=True, text=True).stdout
    if 'active' == stdout.lower().rstrip():
        return True
    else:
        return False

def post_setup():
    anycast_ip_list = make_anycast_ip_list()
    counter = 0
    if counter < 5:
        if check_process_status(name='frr.service') and counter < 3:
            del_bgp_path_v4_v6(anycast_ip_list=anycast_ip_list)
            sys.exit()
        elif counter < 5:
            counter += 1
            time.sleep(1)
        elif counter > 5:
            sys.exit()

if __name__ == '__main__':
    post_setup()
