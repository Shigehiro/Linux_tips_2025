import pulumi
import pulumi_cloudinit as cloudinit
import pulumi_libvirt as libvirt

number_of_vms = 2

def build_network_xslt(ip_range, hosts):
    """
    Return an XSLT string that sets DHCP range and adds multiple host reservations.

    ip_range: dict like {"start": "10.17.3.100", "end": "10.17.3.120"}
    hosts: list of dicts like [{"mac": "...", "ip": "...", "name": "..."}, ...]
    """
    # Build <host .../> elements
    host_entries = "\n".join(
        [f'        <host mac="{h["mac"]}" ip="{h["ip"]}" name="{h.get("name", "")}"/>'
         for h in hosts]
    )

    xslt = f"""<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:dnsmasq="http://libvirt.org/schemas/network/dnsmasq/1.0">
  <xsl:output method="xml" indent="yes"/>

  <!-- Identity transform: copy everything by default -->
  <xsl:template match="@*|node()">
    <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
  </xsl:template>

  <!-- Target the IPv4 <ip> element -->
  <xsl:template match="network/ip[not(@family) or @family='ipv4']">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()[not(self::dhcp)]"/>
      <dhcp>
        <!-- Keep any existing <host> entries, then add ours -->
        <xsl:for-each select="dhcp/host">
          <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
        </xsl:for-each>
        <range start="{ip_range["start"]}" end="{ip_range["end"]}"/>
{host_entries}
      </dhcp>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
"""
    return xslt

ip_range = {"start": "10.17.3.100", "end": "10.17.3.120"}

hosts = [
    {"mac": "52:54:00:aa:bb:01", "ip": "10.17.3.101", "name": "vm-01"},
    {"mac": "52:54:00:aa:bb:02", "ip": "10.17.3.102", "name": "vm-02"},
    {"mac": "52:54:00:aa:bb:03", "ip": "10.17.3.103", "name": "vm-03"},
]

xslt = build_network_xslt(ip_range, hosts)

pulumi_network = libvirt.Network(
    "pulumi_network",
    # IMPORTANT: addresses defines the network gateway/prefix and enables DHCP
    addresses=["10.17.3.1/24"],
    dhcp={"enabled": True},
    dns={"enabled": True, "localOnly": True},
    dnsmasq_options={},  # optional: see notes below
    domain="puluminetwork.local",
    mode="nat",
    xml={"xslt": xslt},
)

for i in range(number_of_vms):

    print(f"VM MAC: {hosts[i]['mac']}")

    pulumi_pool = libvirt.Pool(f"pulumi_pool-{i}",
    type = "dir",
    path = f"/var/lib/libvirt/images/my_pool-{i}"
    )

    pulumi_volume = libvirt.Volume(f"vm-{i}",
      pool   = pulumi_pool.name,
      source = "/home/hattori/Qcow2/Rocky-9-GenericCloud-Base-9.7-20251123.2.x86_64.qcow2",
      format = "qcow2",
    )

    # pool size must be larger than the volume size
    filesystem = libvirt.Volume(f"filesystem-{i}",
      base_volume_id = pulumi_volume.id,
      pool           = pulumi_pool.name,
      size           = 10*1024*1024*1024 # 10GB
    )

    # Define the cloud-init configuration parts
    # Part 1: cloud-config data to install nginx and create a file
    cloud_config_content = """#cloud-config
users:
  - name: hattori
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    groups: sudo, wheel
    ssh_authorized_keys:
        - ssh-ed25519 AAA...
    password: hattori
    chpasswd: {expire: False}
    ssh_pwauth: True
runcmd:
  - echo "Hello from cloud-init!" > /tmp/hello.txt
"""

    # Part 2: a shell script to run
    # When gzip and base64_encode are True, the cloud-init config is not rendered correctly.
    shell_script_content = """#!/bin/bash
echo "This is a shell script part." >> /tmp/cloud-init-log.txt
"""

    cloud_init_config = cloudinit.Config(f"cloud-init-config-{i}",
        parts=[
            cloudinit.ConfigPartArgs(
                content=cloud_config_content,
                content_type="text/cloud-config",
                filename="config.yaml",
            ),
            cloudinit.ConfigPartArgs(
                content=shell_script_content,
                content_type="text/x-shellscript",
                filename="script.sh",
            ),
        ],
        gzip=False,          # Optionally gzip the output
        base64_encode=False  # Optionally base64 encode the output (default)
    )

    cloud_init_disk = libvirt.CloudinitDisk(f"cloudinit-disk-{i}",
        name="vm-cloudinit-disk-{i}.iso",
        user_data=cloud_init_config.rendered, # Pass the rendered MIME config here
        pool = pulumi_pool.name,
    )

    domain = libvirt.Domain(f"vm-{i}",
      type = "kvm",
      graphics = libvirt.DomainGraphicsArgs(type="vnc"),
      autostart = False,
      cpu = {
        "mode": "host-passthrough",
      },
      memory = 2048, # 2GB
      cloudinit = cloud_init_disk.id,
      consoles=[libvirt.DomainConsoleArgs(
        type = "pty",
        target_type = "serial",
        target_port = "0",
      )],
      vcpu = 2,
      disks = [libvirt.DomainDiskArgs(
        volume_id = filesystem.id,
      )],
      network_interfaces = [libvirt.DomainNetworkInterfaceArgs(
        network_id = pulumi_network.id,
        mac = hosts[i]['mac'],
        wait_for_lease = True,
      )],
    )

    pulumi.export(f"vm-{i}", domain.name)