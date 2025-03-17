# Cumulus Linux DNS Anycast load balancing with OSPFv2,v3 and ECMP

- [Cumulus Linux DNS Anycast load balancing with OSPFv2,v3 and ECMP](#cumulus-linux-dns-anycast-load-balancing-with-ospfv2v3-and-ecmp)
  - [Description](#description)
  - [Reference](#reference)
  - [Tested environment](#tested-environment)
  - [Tested software version](#tested-software-version)
  - [Configuration(IPv4,v6 dual stack)](#configurationipv4v6-dual-stack)
    - [Cumulus](#cumulus)
    - [DNS Servers](#dns-servers)
  - [Confirmation](#confirmation)

## Description

Here is how to configure DNS Anycast with Cumulus Linux.

## Reference

- [Open Shortest Path First - OSPF](https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-512/Layer-3/OSPF/#)

## Tested environment

All nodes are running as virtual machines under KVM.
```

10.33.35.0/24                             10.33.36.0/24
2001:0DB8:e::/64                          2001:0DB8:f::/64
<----------------------------->        <--------------------->
Client 10 --- SW --- 254 swp2 Cumulus swp3 254 --- SW --- 10 DNS01
                                                      --- 20 DNS02

                                       <---------OSPF-------->
```

The Cumulus and two DNS servers exchange the routing information via OSPF.<br>

- Client01
  - 10.33.35.10
  - 2001:0DB8:e::10/64
- DNS01
  - 10.33.36.10
  - 2001:0DB8:f::10/64
- DNS02
  - 10.33.36.20
  - 2001:0DB8:f::20/64
- Cumulus
  - 10.33.35.254(swp2)
  - 10.33.36.254(swp3)
  - 2001:0DB8:e::254/64(swp2)
  - 2001:0DB8:f::254/64(swp3)
- Anycast IP 
  - 169.254.0.1(OSPF Area 0)
  - 2001:0DB8:d::1/128(OSPF Area 1)

<br>When the client sends DNS queries to **169.254.0.1 or 2001:0DB8:d::1**, Cumulus routes them to either **DNS01** or **DNS02** using **ECMP**.<br>

## Tested software version

- DNS server
  - Rocky Linux release 9.5 (Blue Onyx)
  - frr-8.5.3-4.el9.x86_64

- Cumulus Linux
  - Cumulus Linux 5.12.0 

## Configuration(IPv4,v6 dual stack)

Here are the configuration files.
- [Cumlus Linux vtysh sh run](./OSPF_config/Cumulus/cumulus_vtysh_sh_run)
- [Cumlus Linux nv config show](./OSPF_config/Cumulus/nv_config_show)
- [DNS01 frr config](./OSPF_config/DNSServer/frr.conf.dns01.ospf)
- [DNS02 frr config](./OSPF_config/DNSServer/frr.conf.dns02.ospf)

### Cumulus

**It seems that Cumulus 5.12 does not support configuring OSPFv3(IPv6) via `nv set`, so I configured both OSPFv2(IPv4) and OSPFv3(IPv6) via `vtysh`.**

enable ospf and ospf6 and restart frr to reflect them.
```
root@ospf-cumulus:mgmt:~# grep -E '^ospfd=|^ospf6d=' /etc/frr/daemons
ospfd=yes
ospf6d=yes
```

```
root@ospf-cumulus:mgmt:~# systemctl restart frr.service 
```

### DNS Servers

Configure anycast IPs on the loopback or dummy interface.
```
nmcli con add con-name dummy0 type dummy ifname dummy0 ipv4.method manual ipv4.addresses 169.254.0.1/32 ipv6.method manual ipv6.addresses 2001:db8:d::1/128
```

<br>Enable ospf and ospf6 and restart frr.
```
dnf install -y frr
```

```
[root@ospf-dns01 ~]# grep -E '^ospfd=|^ospf6d=' /etc/frr/daemons
ospfd=yes
ospf6d=yes
```

```
systemctl restart frr
```

## Confirmation

On the Cumulus:

<br>OSPFv2(IPv4)
```
root@ospf-cumulus:mgmt:~# vtysh -c 'sh ip ospf route'
============ OSPF network routing table ============
N    10.33.36.0/24         [100] area: 0.0.0.0
                           directly attached to swp3
N    169.254.0.1/32        [110] area: 0.0.0.0
                           via 10.33.36.10, swp3
                           via 10.33.36.20, swp3

============ OSPF router routing table =============

============ OSPF external routing table ===========


root@ospf-cumulus:mgmt:~#
```

<br>OSPFv3(IPv6)
```
root@ospf-cumulus:mgmt:~# vtysh -c 'sh ipv6 ospf6 route'
*N IA 2001:db8:d::1/128              fe80::11af:f75a:30f6:d4db   swp3 00:27:50
                                     fe80::7ab2:3621:4e8f:ca10   swp3
*N IA 2001:db8:f::/64                ::                          swp3 00:30:50
root@ospf-cumulus:mgmt:~#
```

Capture OSPFv2 and v3 packets.
```
root@ospf-cumulus:mgmt:~# timeout 30 tcpdump -i swp3 -nn 'ip[9] == 89' or ip6 proto 0x59
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on swp3, link-type EN10MB (Ethernet), snapshot length 262144 bytes
11:26:43.907414 IP 10.33.36.20 > 224.0.0.5: OSPFv2, Hello, length 52
11:26:44.155839 IP 10.33.36.10 > 224.0.0.5: OSPFv2, Hello, length 52
11:26:44.205397 IP6 fe80::11af:f75a:30f6:d4db > ff02::5: OSPFv3, Hello, length 76
11:26:44.205566 IP6 fe80::7ab2:3621:4e8f:ca10 > ff02::5: OSPFv3, Hello, length 76
11:26:49.205214 IP 10.33.36.254 > 224.0.0.5: OSPFv2, Hello, length 52
11:26:49.791103 IP6 fe80::5054:ff:fe53:e6b1 > ff02::5: OSPFv3, Hello, length 76
11:26:53.907402 IP 10.33.36.20 > 224.0.0.5: OSPFv2, Hello, length 52
11:26:54.155918 IP 10.33.36.10 > 224.0.0.5: OSPFv2, Hello, length 52
11:26:54.205589 IP6 fe80::11af:f75a:30f6:d4db > ff02::5: OSPFv3, Hello, length 76
11:26:54.205964 IP6 fe80::7ab2:3621:4e8f:ca10 > ff02::5: OSPFv3, Hello, length 76
11:26:59.205209 IP 10.33.36.254 > 224.0.0.5: OSPFv2, Hello, length 52
11:26:59.791088 IP6 fe80::5054:ff:fe53:e6b1 > ff02::5: OSPFv3, Hello, length 76
11:27:03.907424 IP 10.33.36.20 > 224.0.0.5: OSPFv2, Hello, length 52
11:27:04.155930 IP 10.33.36.10 > 224.0.0.5: OSPFv2, Hello, length 52
11:27:04.205510 IP6 fe80::11af:f75a:30f6:d4db > ff02::5: OSPFv3, Hello, length 76
11:27:04.206005 IP6 fe80::7ab2:3621:4e8f:ca10 > ff02::5: OSPFv3, Hello, length 76
11:27:09.205304 IP 10.33.36.254 > 224.0.0.5: OSPFv2, Hello, length 52
11:27:09.791205 IP6 fe80::5054:ff:fe53:e6b1 > ff02::5: OSPFv3, Hello, length 76
```

```
root@ospf-cumulus:mgmt:~# ps aux |grep -E 'ospfd|ospf6d'|grep -v grep
root       10568  0.0  0.1   7816  3884 ?        S<s  10:52   0:00 /usr/lib/frr/watchfrr -d -F datacenter zebra ospfd ospf6d staticd
frr        10634  0.0  0.2  24316  8884 ?        S<s  10:52   0:00 /usr/lib/frr/ospfd -d -F datacenter -M snmp -A 127.0.0.1
frr        10637  0.0  0.2  23356  8340 ?        S<s  10:52   0:00 /usr/lib/frr/ospf6d -d -F datacenter -M snmp -A ::1
```

Send DNS queries from the DNS client to confirm ECMP works.

IPv4
```
[root@ospf-client01 ~]# for i in $(seq 1 10);do dig @169.254.0.1 version.bind chaos txt +short;done
"dns01"
"dns01"
"dns02"
"dns01"
"dns01"
"dns02"
"dns02"
"dns02"
"dns01"
"dns01"
[root@ospf-client01 ~]#
```

<br>IPv6
```
[root@ospf-client01 ~]# for i in $(seq 1 10); do dig @2001:db8:d::1 version.bind chaos txt +retry=0 +timeout=1 +short;done
"dns02"
"dns01"
"dns01"
"dns01"
"dns01"
"dns01"
"dns02"
"dns02"
"dns01"
"dns01"
[root@ospf-client01 ~]# 
```
