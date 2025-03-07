#!/usr/bin/env python3

"""
Delete anycast IPs from frr.conf

Usage
del_anycast_ip_frr.py -a 169.254.0.1,2001:db8:c::1
"""

import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--anycast_ip', type=str, required=True, help='Specify an Anycast IPs, separated with ,')
parser.add_argument('-c', '--frr_conf', type=str, required=False, default='/etc/frr/frr.conf', help='Specify the config file of frr. Default /etc/frr/frr.conf')
args = parser.parse_args()
anycast_ip = args.anycast_ip.split(',')
frr_conf = args.frr_conf

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

def del_anycast_ip(anycast_ip_list, frr_conf=frr_conf):
    for _, address_list in anycast_ip_list.items():
        for ip in address_list:
            sed_cmd = f'sed /"network.*{ip}\/[0-9]"/d {frr_conf} -i'
            _ = subprocess.run(sed_cmd, shell=True)

def pre_setup():
    anycast_ip_list = make_anycast_ip_list()
    del_anycast_ip(anycast_ip_list=anycast_ip_list, frr_conf=frr_conf)

if __name__ == '__main__':
    pre_setup()
