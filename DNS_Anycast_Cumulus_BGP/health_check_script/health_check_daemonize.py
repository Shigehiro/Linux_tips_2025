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
parser.add_argument('-s', '--server', type=str, default='127.0.0.1', help='Specify a server IP address. Default 127.0.0.1')
parser.add_argument('-a', '--anycast_ip', type=str, required=True, help='Specify an Anycast IP')
parser.add_argument('-as', '--as_number', type=int, required=True, help='Specify a BGP AS number')
parser.add_argument('-i', '--interval', type=int, default=15, help='Specify a check interval. default 15 seconds')
args = parser.parse_args()
qname = args.qname
qtype = args.type
server = args.server
anycast_ip = args.anycast_ip
as_number = args.as_number
interval = args.interval
timeout = 3

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

def add_bgp_path():
    vtysh_cmd = '/usr/bin/vtysh -f /tmp/vtysh.conf'

    command_text = f"""
    router bgp {as_number}
    address-family ipv4 unicast
    network {anycast_ip}/32
    exit
    exit
    exit
    write memory
    exit
    """

    with open('/tmp/vtysh.conf', 'w') as f:
        f.write(command_text)
    subprocess.run(vtysh_cmd.split(), stdout=subprocess.PIPE, stderr = subprocess.PIPE)

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

def check_process_status(name):
    command = f"systemctl is-active {name}"
    stdout = subprocess.run(command.split(), capture_output=True, text=True).stdout
    if 'active' == stdout.lower().rstrip():
        return True
    else:
        return False

def check_ip_in_frr_config(find_string):
    #out = subprocess.run(f"/usr/bin/vtysh -c show run | grep {find_string}", shell=True)
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
    while True:
        udp_result = False
        tcp_result = False

        try:
            # Try the UDP health check
            udp_result = send_query(qname=qname, rdtype=qtype, server=server)

            # If the UDP health check is successful, try the TCP health check.
            if udp_result:
                tcp_result = send_query(qname=qname, rdtype=qtype, server=server, protocol='tcp')

            # Add the anycast IP in BGP
            if udp_result and tcp_result:
                # frr is running and the anycast IP does not exist in the running config, add the BGP path
                if check_process_status(name='frr.service') and not check_ip_in_frr_config(find_string=anycast_ip):
                    add_bgp_path()
                # frr is running and the anycast IP exists in the running config, do nothing
                elif check_process_status(name='frr.service') and check_ip_in_frr_config(find_string=anycast_ip):
                    pass
                
            # Delete the anycast IP from BGP
            else:
                # frr is running and the anycast IP exists in the running config, delete the BGP path
                if check_process_status(name='frr.service') and check_ip_in_frr_config(find_string=anycast_ip):
                    del_bgp_path()
                # frr is running and the anycast IP does not exist in the running config, do nothing
                elif check_process_status(name='frr.service') and not check_ip_in_frr_config(find_string=anycast_ip):
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
