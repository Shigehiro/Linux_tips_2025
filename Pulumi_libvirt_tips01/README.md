# Pulumi Python libvirt: How to Assign a Static IP Address and Hostname via DHCP

## Description

Pulumi’s libvirt.Network resource does not expose every feature available in libvirt’s native XML schema. <br>
When you need to use advanced options or elements that are not supported by Pulumi’s typed properties, you can apply an XSLT stylesheet via the xml={"xslt": ...} parameter. This allows you to transform the provider-generated XML and inject additional libvirt features that aren’t modeled in Pulumi’s schema.<br>

## Sample python script

You can find the [\_\_main\_\_.py](./__main__.py)<br>

When creating the network object, you can use the xml={"xslt": xslt} parameter to apply an XSLT transformation to the generated libvirt network XML.<br>This is useful for adding advanced configurations, such as defining a DHCP lease range and static IP/hostname reservations—that are not exposed by Pulumi’s schema.<br>In the example, the build_network_xslt() function generates an XSLT that injects `<range>` and `<host>` elements into the `<dhcp>` section of the network XML.

`__main__.py`
```python
     59 pulumi_network = libvirt.Network(
     60     "pulumi_network",
     61     # IMPORTANT: addresses defines the network gateway/prefix and enables DHCP
     62     addresses=["10.17.3.1/24"],
     63     dhcp={"enabled": True},
     64     dns={"enabled": True, "localOnly": True},
     65     dnsmasq_options={},  # optional: see notes below
     66     domain="puluminetwork.local",
     67     mode="nat",
     68     xml={"xslt": xslt},
     69 )
```

<br>`__main__.py`
```python
      7 def build_network_xslt(ip_range, hosts):
      8     """
      9     Return an XSLT string that sets DHCP range and adds multiple host reservations.
     10
     11     ip_range: dict like {"start": "10.17.3.100", "end": "10.17.3.120"}
     12     hosts: list of dicts like [{"mac": "...", "ip": "...", "name": "..."}, ...]
     13     """
     14     # Build <host .../> elements
     15     host_entries = "\n".join(
     16         [f'        <host mac="{h["mac"]}" ip="{h["ip"]}" name="{h.get("name", "")}"/>'
     17          for h in hosts]
     18     )
     19
     20     xslt = f"""<?xml version="1.0"?>
     21 <xsl:stylesheet version="1.0"
     22   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
     23   xmlns:dnsmasq="http://libvirt.org/schemas/network/dnsmasq/1.0">
     24   <xsl:output method="xml" indent="yes"/>
     25
     26   <!-- Identity transform: copy everything by default -->
     27   <xsl:template match="@*|node()">
     28     <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
     29   </xsl:template>
     30
     31   <!-- Target the IPv4 <ip> element -->
     32   <xsl:template match="network/ip[not(@family) or @family='ipv4']">
     33     <xsl:copy>
     34       <xsl:apply-templates select="@*|node()[not(self::dhcp)]"/>
     35       <dhcp>
     36         <!-- Keep any existing <host> entries, then add ours -->
     37         <xsl:for-each select="dhcp/host">
     38           <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
     39         </xsl:for-each>
     40         <range start="{ip_range["start"]}" end="{ip_range["end"]}"/>
     41 {host_entries}
     42       </dhcp>
     43     </xsl:copy>
     44   </xsl:template>
     45 </xsl:stylesheet>
     46 """
     47     return xslt
     48
     49 ip_range = {"start": "10.17.3.100", "end": "10.17.3.120"}
     50
     51 hosts = [
     52     {"mac": "52:54:00:aa:bb:01", "ip": "10.17.3.101", "name": "vm-01"},
     53     {"mac": "52:54:00:aa:bb:02", "ip": "10.17.3.102", "name": "vm-02"},
     54     {"mac": "52:54:00:aa:bb:03", "ip": "10.17.3.103", "name": "vm-03"},
     55 ]
```

## Walkthrough logs

Set an appropriate SSH keys in `ssh_authorized_keys:`<br>

Launch two VMs.
```
$ pulumi up -y
Previewing update (dev):
     Type                            Name                 Plan       Info
 +   pulumi:pulumi:Stack             libvirt_work-dev     create     2 messages
 +   ├─ libvirt:index:Pool           pulumi_pool-0        create
 +   ├─ libvirt:index:Network        pulumi_network       create
 +   ├─ libvirt:index:Pool           pulumi_pool-1        create
 +   ├─ cloudinit:index:Config       cloud-init-config-0  create
 +   ├─ cloudinit:index:Config       cloud-init-config-1  create
 +   ├─ libvirt:index:Volume         vm-0                 create
 +   ├─ libvirt:index:Volume         vm-1                 create
 +   ├─ libvirt:index:CloudinitDisk  cloudinit-disk-0     create
 +   ├─ libvirt:index:CloudinitDisk  cloudinit-disk-1     create
 +   ├─ libvirt:index:Volume         filesystem-0         create
 +   ├─ libvirt:index:Volume         filesystem-1         create
 +   ├─ libvirt:index:Domain         vm-0                 create
 +   └─ libvirt:index:Domain         vm-1                 create

Diagnostics:
  pulumi:pulumi:Stack (libvirt_work-dev):
    VM MAC: 52:54:00:aa:bb:01
    VM MAC: 52:54:00:aa:bb:02

Outputs:
    vm-0: "vm-0-6330c99"
    vm-1: "vm-1-29023be"

Resources:
    + 14 to create

Updating (dev):
     Type                            Name                 Status              Info
 +   pulumi:pulumi:Stack             libvirt_work-dev     created (27s)       2 messages
 +   ├─ libvirt:index:Pool           pulumi_pool-0        created (0.22s)
 +   ├─ libvirt:index:Network        pulumi_network       created (0.38s)
 +   ├─ cloudinit:index:Config       cloud-init-config-0  created (0.01s)
 +   ├─ cloudinit:index:Config       cloud-init-config-1  created (0.00s)
 +   ├─ libvirt:index:Pool           pulumi_pool-1        created (0.22s)
 +   ├─ libvirt:index:Volume         vm-0                 created (3s)
 +   ├─ libvirt:index:Volume         vm-1                 created (3s)
 +   ├─ libvirt:index:CloudinitDisk  cloudinit-disk-1     created (3s)
 +   ├─ libvirt:index:CloudinitDisk  cloudinit-disk-0     created (3s)
 +   ├─ libvirt:index:Volume         filesystem-0         created (0.03s)
 +   ├─ libvirt:index:Volume         filesystem-1         created (0.03s)
 +   ├─ libvirt:index:Domain         vm-0                 created (23s)
 +   └─ libvirt:index:Domain         vm-1                 created (13s)       

Diagnostics:
  pulumi:pulumi:Stack (libvirt_work-dev):
    VM MAC: 52:54:00:aa:bb:01
    VM MAC: 52:54:00:aa:bb:02

Outputs:
    vm-0: "vm-0-9721104"
    vm-1: "vm-1-79e52fe"

Resources:
    + 14 created

Duration: 28s
```

<br>The static IPs were assigned to them.
```
$ sudo virsh list | grep vm-
 42   vm-0-9721104     running
 43   vm-1-79e52fe     running

$ sudo virsh domifaddr 42
 Name       MAC address          Protocol     Address
-------------------------------------------------------------------------------
 vnet42     52:54:00:aa:bb:01    ipv4         10.17.3.101/24

$ sudo virsh domifaddr 43
 Name       MAC address          Protocol     Address
-------------------------------------------------------------------------------
 vnet43     52:54:00:aa:bb:02    ipv4         10.17.3.102/24
```

<br>Check the hostname of VMs.
```
$ ssh 10.17.3.101 hostname
vm-01

$ ssh 10.17.3.102 hostname
vm-02
```