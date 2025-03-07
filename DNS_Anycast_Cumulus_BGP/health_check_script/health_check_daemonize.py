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
parser.add_argument('-q', '--qname', type=str, required=True, help='Specify a query name')
parser.add_argument('-t', '--type', type=str, default='A', help='Specify a query type. Default A')
parser.add_argument('-a', '--anycast_ip', type=str, required=True, help='Specify an Anycast IP')
parser.add_argument('-as', '--as_number', type=int, required=True, help='Specify a BGP AS number')
parser.add_argument('-i', '--interval', type=int, default=15, help='Specify a check interval. default 15 seconds')
args = parser.parse_args()
qname = args.qname
qtype = args.type
anycast_ip = args.anycast_ip.split(',')
as_number = args.as_number
interval = args.interval
timeout = 3

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

def send_query(qname, rdtype, server, protocol='udp'):
    # Construct a query
    q = dns.message.make_query(qname=qname, rdtype=qtype)

    # health check result
    health_result = False

    # Send a query over UDP
    if protocol == 'udp':
        try:
            _ = dns.query.udp(q, where=server, timeout=timeout)
            health_result = True
        except Exception as _:
            pass
    # Send a query over TCP
    elif protocol == 'tcp':
        try:
            _ = dns.query.tcp(q, where=server, timeout=timeout)
            health_result = True
        except Exception as _:
            pass

    return health_result

def update_route_vtysh(ip, as_number, operation, address_family):
    vtysh_cmd = '/usr/bin/vtysh -f /tmp/vtysh_health.conf'

    if operation == 'delete' and address_family == 'ipv4':
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

        with open('/tmp/vtysh_health.conf', 'w') as f:
            f.write(command_text)
        subprocess.run(vtysh_cmd.split(), stdout=subprocess.PIPE, stderr = subprocess.PIPE)

    elif operation == 'add' and address_family == 'ipv4':
        command_text = f"""
        router bgp {as_number}
        address-family ipv4 unicast
        network {ip}/32
        exit
        exit
        exit
        write memory
        exit
        """

        with open('/tmp/vtysh_health.conf', 'w') as f:
            f.write(command_text)
        subprocess.run(vtysh_cmd.split(), stdout=subprocess.PIPE, stderr = subprocess.PIPE)

    elif operation == 'delete' and address_family == 'ipv6':
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

        with open('/tmp/vtysh_health.conf', 'w') as f:
            f.write(command_text)
        subprocess.run(vtysh_cmd.split(), stdout=subprocess.PIPE, stderr = subprocess.PIPE)

    elif operation == 'add' and address_family == 'ipv6':
        command_text = f"""
        router bgp {as_number}
        address-family ipv6 unicast
        network {ip}/128
        exit
        exit
        exit
        write memory
        exit
        """

        with open('/tmp/vtysh_health.conf', 'w') as f:
            f.write(command_text)
        subprocess.run(vtysh_cmd.split(), stdout=subprocess.PIPE, stderr = subprocess.PIPE)

def check_process_status(name):
    command = f"systemctl is-active {name}"
    stdout = subprocess.run(command.split(), capture_output=True, text=True).stdout
    if 'active' == stdout.lower().rstrip():
        return True
    else:
        return False

def check_ip_in_frr_config(find_string):
    ps1 = subprocess.Popen(['/usr/bin/vtysh', '-c', 'show run'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ps2 = subprocess.Popen(['grep', find_string], stdin=ps1.stdout, stdout=subprocess.PIPE)
    ps1.stdout.close()
    out, _ = ps2.communicate()
    # Coud find the string
    if find_string in out.decode('utf-8'):
        return True
    # Could not find the string
    else:
        return False

def config_frr_by_health_check():
    anycast_ip_list = make_anycast_ip_list()

    while True:
        for address_family ,address_list in anycast_ip_list.items():
            for ip in address_list:

                udp_result = False
                tcp_result = False

                try:
                    # Try the UDP health check
                    udp_result = send_query(qname=qname, rdtype=qtype, server=ip)

                    # If the UDP health check is successful, try the TCP health check.
                    if udp_result:
                        tcp_result = send_query(qname=qname, rdtype=qtype, server=ip, protocol='tcp')

                    # Add the anycast IP in BGP
                    if udp_result and tcp_result:
                        # frr is running and the anycast IP does not exist in the running config, add the BGP path
                        if check_process_status(name='frr.service') and not check_ip_in_frr_config(find_string=ip):
                            update_route_vtysh(ip=ip, as_number=as_number, operation='add', address_family=address_family)
                        # frr is running and the anycast IP exists in the running config, do nothing
                        elif check_process_status(name='frr.service') and check_ip_in_frr_config(find_string=ip):
                            pass
                        
                    # Delete the anycast IP from BGP
                    else:
                        # frr is running and the anycast IP exists in the running config, delete the BGP path
                        if check_process_status(name='frr.service') and check_ip_in_frr_config(find_string=ip):
                            update_route_vtysh(ip=ip, as_number=as_number, operation='delete', address_family=address_family)
                        # frr is running and the anycast IP does not exist in the running config, do nothing
                        elif check_process_status(name='frr.service') and not check_ip_in_frr_config(find_string=ip):
                            pass
                except:
                    pass
                finally:
                    time.sleep(interval)

# fork
def daemonize():
    pid = os.fork()
    # parent process
    if pid > 0:
        pid_file = open('/var/run/config_frr_health_check.pid','w')
        pid_file.write(str(pid)+"\n")
        pid_file.close()
        sys.exit()
    # child process
    if pid == 0:
        config_frr_by_health_check()

if __name__ == '__main__':
    while True:
        daemonize()
