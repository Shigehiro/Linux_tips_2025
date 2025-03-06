# Cumulus Linux DNS Anycast load balancing with BGP and ECMP

- [Cumulus Linux DNS Anycast load balancing with BGP and ECMP](#cumulus-linux-dns-anycast-load-balancing-with-bgp-and-ecmp)
  - [Description](#description)
  - [Reference](#reference)
  - [Tested environment](#tested-environment)
  - [Configuration](#configuration)
    - [DNS Server](#dns-server)
      - [Only IPv4](#only-ipv4)
        - [Configure the anycast IP in the loopback address, install frr, enable BGP.](#configure-the-anycast-ip-in-the-loopback-address-install-frr-enable-bgp)
        - [Configure frr](#configure-frr)
        - [Cumulus Linux](#cumulus-linux)
      - [IPv4, IPv6 dual stack, exchange routing information of both IPv4 and IPv6 with BGP over IPv6 addresses](#ipv4-ipv6-dual-stack-exchange-routing-information-of-both-ipv4-and-ipv6-with-bgp-over-ipv6-addresses)
    - [DNS servers](#dns-servers)
    - [Cumulus Linux](#cumulus-linux-1)
  - [Confirm ECMP works](#confirm-ecmp-works)
  - [Add or remove the route path over BGP based on the application health check result](#add-or-remove-the-route-path-over-bgp-based-on-the-application-health-check-result)
  - [Logs](#logs)
  - [Use dummy interface instead of loopback interface](#use-dummy-interface-instead-of-loopback-interface)

## Description

Here is how to configure DNS Anycast with Cumulus Linux.

## Reference

- [Border Gateway Protocol - BGP](https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-512/Layer-3/Border-Gateway-Protocol-BGP/#)
- [Equal Cost Multipath Load Sharing](https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-512/Layer-3/Routing/Equal-Cost-Multipath-Load-Sharing/)
- [Troubleshooting BGP](https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-512/Layer-3/Border-Gateway-Protocol-BGP/Troubleshooting-BGP/)
- [IPv4/IPv6の両方の通信を試験可能なFRRoutingのdocker composeサンプル](IPv4/IPv6の両方の通信を試験可能なFRRoutingのdocker composeサンプル)

## Tested environment

All nodes are running as virtual machines under KVM.
```

10.33.33.0/24                     10.33.34.0/24
<------------------------->    <----------------->
Client 10 --- SW --- 254 Cumulus 254 --- SW --- 10 DNS01
                                            --- 20 DNS02

                               <-------BGP-------->
```

The Cumulus and two DNS servers exchange the routing information via BGP.<br>

- Client01
  - 10.33.33.10
  - 2001:0DB8:a::10/64
- DNS01
  - 10.33.34.10
  - 2001:0DB8:b::10/64
- DNS02
  - 10.33.34.20
  - 2001:0DB8:b::20/64
- Cumulus
  - 10.33.33.254
  - 10.33.34.254
  - 2001:0DB8:a::254/64
  - 2001:0DB8:b::254/64
- Anycast IP 
  - 169.254.0.1 ( Configure this IP on both DNS servers as a loopback address)
  - 2001:0DB8:c::1/64
- AS Number of Cumulus : 64512
- AS Number of DNS01, DNS02 : 64513

<br>When the client sends DNS queries to **169.254.0.1**, Cumulus routes them to either **DNS01** or **DNS02** using **ECMP**.<br>
DNS01 and DNS02 have the same AS number.

## Configuration

### DNS Server

#### Only IPv4

You can find the config under:
- DNS servers
  - dns01_02_frr_config/v4_only/
- Cumulus Linux
  - cumulus_linux_config/v4_only/

##### Configure the anycast IP in the loopback address, install frr, enable BGP.

Configure the anycast IPv4
```
ansible -i inventory.ini all -m shell -a "nmcli con del lo ; nmcli con add connection.id lo connection.type loopback connection.interface-name lo connection.autoconnect yes ; nmcli con mod lo +ipv4.addresses 169.254.0.1/32 ; nmcli device reapply lo"
```

IPv6 for the anycast.
```
ansible -i inventory.ini all -m shell \
-a "nmcli con mod lo +ipv6.addresses 2001:0DB8:c::1/128 ; nmcli device reapply lo"
```

Install frr
```
ansible -i inventory.ini all -m shell -a 'dnf install -y frr'
```

Enable BGP
```
ansible -i inventory.ini all -m shell -a "sed s/bgpd=no/bgpd=yes/ /etc/frr/daemons -i"
```

Start frr
```
ansible -i inventory.ini all -m shell -a 'systemctl enable frr.service --now'
```

##### Configure frr

DNS01
```
[root@dns01 ~]# cat /etc/frr/frr.conf
hostname dns01
no ip forwarding
no ipv6 forwarding
!
router bgp 64513
 bgp router-id 10.33.34.10
 neighbor 10.33.34.254 remote-as 64512
 neighbor 10.33.34.254 password password
 neighbor 10.33.34.254 update-source 10.33.34.10
 !
 address-family ipv4 unicast
  network 169.254.0.1/32
  neighbor 10.33.34.254 soft-reconfiguration inbound
  neighbor 10.33.34.254 route-map route-map-from-peers in
  neighbor 10.33.34.254 route-map route-map-to-peers out
 exit-address-family
exit
!
route-map route-map-from-peers permit 9999
exit
!
route-map route-map-to-peers permit 9999
exit
!
[root@dns01 ~]#
```

DNS02
```
[root@dns02 ~]# cat /etc/frr/frr.conf
hostname dns02
no ip forwarding
no ipv6 forwarding
!
router bgp 64513
 bgp router-id 10.33.34.20
 neighbor 10.33.34.254 remote-as 64512
 neighbor 10.33.34.254 password password
 neighbor 10.33.34.254 update-source 10.33.34.20
 !
 address-family ipv4 unicast
  network 169.254.0.1/32
  neighbor 10.33.34.254 soft-reconfiguration inbound
  neighbor 10.33.34.254 route-map route-map-from-peers in
  neighbor 10.33.34.254 route-map route-map-to-peers out
 exit-address-family
exit
!
route-map route-map-from-peers permit 9999
exit
!
route-map route-map-to-peers permit 9999
exit
!
[root@dns02 ~]#
```

##### Cumulus Linux

```
cumulus@switch:~$ nv set router bgp autonomous-system 64512
cumulus@switch:~$ nv set router bgp router-id 10.33.34.254
cumulus@cumulus:mgmt:~$ nv set vrf default router bgp neighbor 10.33.34.10 password password
cumulus@cumulus:mgmt:~$ nv set vrf default router bgp neighbor 10.33.34.10 remote-as external 
cumulus@cumulus:mgmt:~$ nv set vrf default router bgp neighbor 10.33.34.20 password password
cumulus@cumulus:mgmt:~$ nv set vrf default router bgp neighbor 10.33.34.20 remote-as external 
cumulus@cumulus:mgmt:~$ nv config apply
```

```
cumulus@cumulus:mgmt:~$ nv show vrf default router bgp neighbor

AS - Remote Autonomous System, PeerEstablishedTime - Peer established time in
UTC format, UpTime - Last connection reset time in days,hours:min:sec, Afi-Safi
- Address family, PfxSent - Transmitted prefix counter, PfxRcvd - Recieved
prefix counter

Neighbor     AS     State        PeerEstablishedTime   UpTime    MsgRcvd  MsgSent  Afi-Safi      PfxSent  PfxRcvd
-----------  -----  -----------  --------------------  --------  -------  -------  ------------  -------  -------
10.33.34.10  64513  established  2025-02-25T12:40:29Z  17:17:57  20795    20802    ipv4-unicast  1        1
10.33.34.20  64513  established  2025-02-25T12:40:30Z  17:17:57  20781    20787    ipv4-unicast  1        1
```

```
cumulus@cumulus:mgmt:~$ nv show vrf default router rib ipv4 route 169.254.0.1/32
route-entry
==============

    Protocol - Protocol name, TblId - Table Id, NHGId - Nexthop group Id, Flags - u
    - unreachable, r - recursive, o - onlink, i - installed, d - duplicate, c -
    connected, A - active

    EntryIdx  Protocol  TblId  NHGId  Distance  Metric  ResolvedVia  ResolvedViaIntf  Weight  Flags
    --------  --------  -----  -----  --------  ------  -----------  ---------------  ------  -----
    1         bgp       254    67     20        0       10.33.34.10  swp3             1       iA
                                                        10.33.34.20  swp3             1       iA
cumulus@cumulus:mgmt:~$
```

You can check BGP info as below.
```
cumulus@cumulus:mgmt:~$ nv show vrf default router bgp [sub command]
```

```
cumulus@cumulus:mgmt:~$ sudo vtysh -c 'show ip bgp ipv4 unicast'
BGP table version is 25, local router ID is 10.33.34.254, vrf id 0
Default local pref 100, local AS 64512
Status codes:  s suppressed, d damped, h history, u unsorted, * valid, > best, = multipath, + multipath nhg,
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

   Network          Next Hop            Metric LocPrf Weight Path
*> 169.254.0.1/32   10.33.34.10(dns01)
                                             0             0 64513 i
*=                  10.33.34.20(dns02)
                                             0             0 64513 i

Displayed  1 routes and 2 total paths
```

```
cumulus@cumulus:mgmt:~$ sudo vtysh -c 'show ip bgp summary'

IPv4 Unicast Summary (VRF default):
BGP router identifier 10.33.34.254, local AS number 64512 vrf-id 0
BGP table version 25
RIB entries 1, using 224 bytes of memory
Peers 2, using 40 KiB of memory

Neighbor           V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd   PfxSnt Desc
dns01(10.33.34.10) 4      64513     21487     21494        0    0    0 17:52:29            1        1 N/A
dns02(10.33.34.20) 4      64513     21473     21479        0    0    0 17:52:28            1        1 N/A

Total number of neighbors 2
```

```
cumulus@cumulus:mgmt:~$ sudo cat /etc/frr/frr.conf
# Auto-generated by NVUE!
# Any local modifications will prevent NVUE from re-generating this file.
# md5sum: 97217447712e7feacba5d2541ca4aa1c
!---- Cumulus Defaults ----
frr defaults datacenter
log syslog informational
!---- Rendered frr.conf ----
vrf mgmt
exit-vrf
router bgp 64512 vrf default
bgp router-id 10.33.34.254
timers bgp 3 9
bgp deterministic-med
! Neighbors
neighbor 10.33.34.10 remote-as external
neighbor 10.33.34.10 password password
neighbor 10.33.34.10 timers 3 9
neighbor 10.33.34.10 timers connect 10
neighbor 10.33.34.10 advertisement-interval 0
no neighbor 10.33.34.10 capability extended-nexthop
neighbor 10.33.34.20 remote-as external
neighbor 10.33.34.20 password password
neighbor 10.33.34.20 timers 3 9
neighbor 10.33.34.20 timers connect 10
neighbor 10.33.34.20 advertisement-interval 0
no neighbor 10.33.34.20 capability extended-nexthop
! Address families
address-family ipv4 unicast
maximum-paths ibgp 64
maximum-paths 64
distance bgp 20 200 200
neighbor 10.33.34.10 activate
neighbor 10.33.34.20 activate
exit-address-family
! end of router bgp 64512 vrf default
!---- NVUE snippets ----
cumulus@cumulus:mgmt:~$
```

#### IPv4, IPv6 dual stack, exchange routing information of both IPv4 and IPv6 with BGP over IPv6 addresses

You can find the config under:
- DNS servers
  - dns01_02_frr_config/dual_stack_BGP_over_v6/
- Cumulus Linux
  - cumulus_linux_config/dual_stack_BGP_over_v6/

### DNS servers

I configured anycast addresses as a dummy interface instead of loopback interface.
```
nmcli connection add type dummy ifname dummy0 ipv4.method manual ipv4.addresses 169.254.0.1/32 ipv6.method manual ipv6.addresses 2001:db8:c::1/128
```

```
nmcli device reapply dummy0
```

You need to add IPv6 address on eth0 as well.

<br>DNS01
```
[root@dns01 ~]# ip a s | grep -E '^[1-9]|inet'
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    inet 127.0.0.1/8 scope host lo
    inet6 ::1/128 scope host
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    inet 10.33.34.10/24 brd 10.33.34.255 scope global noprefixroute eth0
    inet6 2001:db8:b::10/64 scope global noprefixroute
    inet6 fe80::8b7b:fa30:1886:3186/64 scope link noprefixroute
5: dummy0: <BROADCAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default qlen 1000
    inet 169.254.0.1/32 scope link noprefixroute dummy0
    inet6 2001:db8:c::1/128 scope global noprefixroute
    inet6 fe80::97bc:6137:c634:3b0e/64 scope link noprefixroute
```

<br>DNS02
```
[root@dns01 ~]# ansible -i inventory.ini dns02 -m shell -a "ip a s | grep -E '^[1-9]|inet'"
dns02 | CHANGED | rc=0 >>
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    inet 127.0.0.1/8 scope host lo
    inet 169.254.0.1/32 scope link lo
    inet6 2001:db8:c::1/128 scope global
    inet6 ::1/128 scope host
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    inet 10.33.34.20/24 brd 10.33.34.255 scope global noprefixroute eth0
    inet6 2001:db8:b::20/64 scope global noprefixroute
    inet6 fe80::4ee7:b222:7453:9ce9/64 scope link noprefixroute
3: dummy0: <BROADCAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default qlen 1000
    inet 169.254.0.1/32 scope link noprefixroute dummy0
    inet6 2001:db8:c::1/128 scope global noprefixroute
    inet6 fe80::b0ba:4ed4:536a:31c6/64 scope link noprefixroute
```

### Cumulus Linux

```
cumulus@cumulus:mgmt:~$ nv show vrf default router rib ipv4 route 169.254.0.1/32
route-entry
==============

    Protocol - Protocol name, TblId - Table Id, NHGId - Nexthop group Id, Flags - u
    - unreachable, r - recursive, o - onlink, i - installed, d - duplicate, c -
    connected, A - active

    EntryIdx  Protocol  TblId  NHGId  Distance  Metric  ResolvedVia  ResolvedViaIntf  Weight  Flags
    --------  --------  -----  -----  --------  ------  -----------  ---------------  ------  -----
    1         bgp       254    337    20        0       10.33.34.10  swp3             1       iA   
                                                        10.33.34.20  swp3             1       iA   
```

```
cumulus@cumulus:mgmt:~$ nv show vrf default router rib ipv6 route 2001:db8:c::1/128
route-entry
==============

    Protocol - Protocol name, TblId - Table Id, NHGId - Nexthop group Id, Flags - u
    - unreachable, r - recursive, o - onlink, i - installed, d - duplicate, c -
    connected, A - active

    EntryIdx  Protocol  TblId  NHGId  Distance  Metric  ResolvedVia                ResolvedViaIntf  Weight  Flags
    --------  --------  -----  -----  --------  ------  -------------------------  ---------------  ------  -----
    1         bgp       254    339    20        0       fe80::4ee7:b222:7453:9ce9  swp3             1       iA   
                                                        fe80::8b7b:fa30:1886:3186  swp3             1       iA   
cumulus@cumulus:mgmt:~$ 
```

## Confirm ECMP works

Send DNS queries to the anycast IP from the client.
```
[root@client01 ~]# for i in $(seq 1 10);do dig @169.254.0.1 version.bind chaos txt +short ;done
"dns01"
"dns01"
"dns02"
"dns02"
"dns01"
"dns01"
"dns02"
"dns01"
"dns01"
"dns02"
[root@client01 ~]# 
```

```
[root@client01 ~]# for i in $(seq 1 10);do dig @2001:db8:c::1 version.bind chaos txt +short ;done
"dns02"
"dns01"
"dns01"
"dns02"
"dns02"
"dns02"
"dns01"
"dns02"
"dns01"
"dns01"
[root@client01 ~]#
```

## Add or remove the route path over BGP based on the application health check result

Add the health check script to add or remove the route path over BGP based on the DNS health check result.<br>

Copy health_check_daemonize.py and del_bgp_path.py under /root directory.
```
# ls /root/*.py
/root/del_bgp_path.py  /root/health_check_daemonize.py
```

Copy the unit filer config_frr_by_health_check.service under /usr/lib/systemd/system/ and issue daemon-reload to reflect that.
```
# cp config_frr_by_health_check.service /usr/lib/systemd/system
# systemctl daemon-reload
# systemctl enable config_frr_by_health_check.service --now
```

Here is the routeing information after stopping DNS daemon on the DNS01 box.
You can see the route path to the DNS01(10.33.34.10) has been removed.
```
cumulus@cumulus:mgmt:~$ sudo vtysh -c 'show ip bgp ipv4 unicast'
[sudo] password for cumulus:
BGP table version is 26, local router ID is 10.33.34.254, vrf id 0
Default local pref 100, local AS 64512
Status codes:  s suppressed, d damped, h history, u unsorted, * valid, > best, = multipath, + multipath nhg,
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

   Network          Next Hop            Metric LocPrf Weight Path
*> 169.254.0.1/32   10.33.34.20(dns02)
                                             0             0 64513 i

Displayed  1 routes and 1 total paths
cumulus@cumulus:mgmt:~$
```

After starting DNS daemon on the DNS01 box.<br>
The route path to the DNS01 has been added.
```
cumulus@cumulus:mgmt:~$ sudo vtysh -c 'show ip bgp ipv4 unicast'
BGP table version is 27, local router ID is 10.33.34.254, vrf id 0
Default local pref 100, local AS 64512
Status codes:  s suppressed, d damped, h history, u unsorted, * valid, > best, = multipath, + multipath nhg,
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

   Network          Next Hop            Metric LocPrf Weight Path
*> 169.254.0.1/32   10.33.34.20(dns02)
                                             0             0 64513 i
*=                  10.33.34.10(dns01)
                                             0             0 64513 i

Displayed  1 routes and 2 total paths
cumulus@cumulus:mgmt:~$
```

<br>You might want to confirm if this works when rebooting the OS as well.

## Logs

- Cumulus linux
  - /var/log/frr/frr.log

- FRR on DNS servers
  - enable log, check journal logs.
    ```
    # grep ^log /etc/frr/frr.conf
    log syslog informational
    ```

## Use dummy interface instead of loopback interface

[Chapter 16. Creating a dummy interface](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/configuring_and_managing_networking/creating-a-dummy-interface_configuring-and-managing-networking#creating-a-dummy-interface_configuring-and-managing-networking)

```
# nmcli connection add type dummy ifname dummy0 ipv4.method manual ipv4.addresses 169.254.0.1/32 ipv6.method manual ipv6.addresses 2001:db8:c::1/128
Connection 'dummy-dummy0' (91da8834-13f9-4dab-9d12-56ace863d636) successfully added.
```

```
# nmcli device reapply dummy0
Connection successfully reapplied to device 'dummy0'.
```

```
# ip a s dummy0
3: dummy0: <BROADCAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default qlen 1000
    link/ether ca:0e:20:c1:3f:82 brd ff:ff:ff:ff:ff:ff
    inet 169.254.0.1/32 scope link noprefixroute dummy0
       valid_lft forever preferred_lft forever
    inet6 2001:db8:c::1/128 scope global noprefixroute
       valid_lft forever preferred_lft forever
    inet6 fe80::a375:f2cd:6c30:11d5/64 scope link noprefixroute
       valid_lft forever preferred_lft forever
```