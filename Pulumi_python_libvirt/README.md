# Pulumi and python libvirt

- [Pulumi and python libvirt](#pulumi-and-python-libvirt)
  - [Description](#description)
  - [Reference](#reference)
  - [Examples](#examples)
    - [Launch single VM, no cloud-init](#launch-single-vm-no-cloud-init)
    - [Launch single VM with cloud-init](#launch-single-vm-with-cloud-init)
    - [Multiple VMs with cloud-init](#multiple-vms-with-cloud-init)
    - [Multiple VMs, no cloud-init](#multiple-vms-no-cloud-init)
  - [Erros I saw](#erros-i-saw)
    - [Can't not create a project with pulumi new behind transparent proxy](#cant-not-create-a-project-with-pulumi-new-behind-transparent-proxy)
    - [failed to connect: authentication unavailable: no polkit agent available to authenticate action 'org.libvirt.unix.manage':](#failed-to-connect-authentication-unavailable-no-polkit-agent-available-to-authenticate-action-orglibvirtunixmanage)
    - [error defining libvirt domain: unsupported configuration: spice graphics are not supported with this QEMU:](#error-defining-libvirt-domain-unsupported-configuration-spice-graphics-are-not-supported-with-this-qemu)

## Description

Here is how to launch VMs with Pulumi and python-libvirt.

## Reference

- [Pulumi start | libvirt-python series](https://someideas.net/posts/2022-06-18-pulumi_libvirt-series/)
- [libvirt: API Docs](https://www.pulumi.com/registry/packages/libvirt/api-docs/)
- [Spin up a Ubuntu VM using Pulumi and libvirt](https://dustinspecker.com/posts/ubuntu-vm-pulumi-libvirt/)

## Examples

### Launch single VM, no cloud-init

```
mkdir Pulumi_work

cd Pulumi_work/

pulumi login file://./

mkdir libvirt_work

cd libvirt_work/
```

Create a project:
```
pulumi new python
```

Add the terraform provider:
```
pulumi package add terraform-provider registry.opentofu.org/dmacvicar/libvirt
```

Set the libvirt URI:
```
pulumi config set libvirt:uri qemu:///system
```

```
$ pulumi config
KEY          VALUE
libvirt:uri  qemu:///system
pulumi:tags  {"pulumi:template":"python"}
```

Edit `__main__.py` as shown below.
```python
import pulumi
import pulumi_libvirt as libvirt

pulumi_pool = libvirt.Pool("pulumi_pool",
  type = "dir",
  path = "/var/lib/libvirt/images/my_pool"
)

cent10 = libvirt.Volume("cent10",
  pool   = pulumi_pool.name,
  source = "/home/hattori/Qcow2/CentOS-Stream-GenericCloud-10-20251027.0.x86_64-no-cloud-init.qcow2",
  format = "qcow2",
)

# pool size must be larger than the volume size
filesystem = libvirt.Volume("filesystem",
  base_volume_id = cent10.id,
  pool           = pulumi_pool.name,
  size           = 10*1024*1024*1024 # 10GB
)

pulumi_network = libvirt.Network("pulumi_network",
    addresses=[
        "10.17.3.0/24",
    ],
    dns={
        "enabled": True,
        "local_only": True,
    },
    dnsmasq_options={},
    domain="puluminetwork.local",
    mode="nat")

domain = libvirt.Domain("cent10",
  type = "kvm",
  graphics = libvirt.DomainGraphicsArgs(type="vnc"),
  autostart = False,
  cpu = {
    "mode": "host-passthrough",
  },
  memory = 2048, # 2GB
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
    wait_for_lease = True,
  )],
)

pulumi.export("VM name", domain.name)
pulumi.export("VM IP", pulumi_network.addresses[0])
```

```
export PULUMI_CONFIG_PASSPHRASE=secret
```

Create the libvirt domain.
```
$ pulumi up -y
Previewing update (dev):
     Type                     Name              Plan       
 +   pulumi:pulumi:Stack      libvirt_work-dev  create     
 +   └─ libvirt:index:Domain  test01            create     

Resources:
    + 2 to create

Updating (dev):
     Type                     Name              Status              
 +   pulumi:pulumi:Stack      libvirt_work-dev  created (0.46s)     
 +   └─ libvirt:index:Domain  test01            created (0.38s)     

Resources:
    + 2 created

Duration: 1s
```

```
$ sudo virsh list 
 Id   Name             State
--------------------------------
 2    test01-175377f   running
```

Destroy the domain:
```
pulumi destroy -y
```

### Launch single VM with cloud-init

```
mkdir single_vm_with_cloud_init

cd single_vm_with_cloud_init

pulumi new python

pulumi package add terraform-provider registry.opentofu.org/dmacvicar/libvirt

./venv/bin/pip install pulumi_cloudinit

pulumi config set libvirt:uri qemu:///system
```

<br>`__main__.py`
```python
import pulumi
import pulumi_cloudinit as cloudinit
import pulumi_libvirt as libvirt

pulumi_pool = libvirt.Pool("pulumi_pool",
  type = "dir",
  path = "/var/lib/libvirt/images/my_pool"
)

cent10 = libvirt.Volume("cent10",
  pool   = pulumi_pool.name,
  source = "/home/hattori/Qcow2/CentOS-Stream-GenericCloud-10-20251027.0.x86_64.qcow2",
  format = "qcow2",
)

# pool size must be larger than the volume size
filesystem = libvirt.Volume("filesystem",
  base_volume_id = cent10.id,
  pool           = pulumi_pool.name,
  size           = 10*1024*1024*1024 # 10GB
)

pulumi_network = libvirt.Network("pulumi_network",
    addresses=[
        "10.17.3.0/24",
    ],
    dns={
        "enabled": True,
        "local_only": True,
    },
    dnsmasq_options={},
    domain="puluminetwork.local",
    mode="nat")

# Define the cloud-init configuration parts
# Part 1: cloud-config data to install nginx and create a file
cloud_config_content = """#cloud-config
users:
  - name: centos
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    groups: sudo, wheel
    ssh_authorized_keys:
        - ssh-rsa AAAAB...
    password: centos
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

cloud_init_config = cloudinit.Config("cloud-init-config",
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


cloud_init_disk = libvirt.CloudinitDisk("cloudinit-disk",
    name="vm-cloudinit-disk.iso",
    user_data=cloud_init_config.rendered, # Pass the rendered MIME config here
    pool = pulumi_pool.name,
)

domain = libvirt.Domain("cent10",
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
    wait_for_lease = True,
  )],
)

pulumi.export("VM name", domain.name)
pulumi.export("cloud_init_output", cloud_init_config.rendered)
```

```
pulumi up -y
```

```
$ sudo virsh list 
 Id   Name             State
--------------------------------
 8    cent10-3037edc   running
```

Confirm you can access the VM with SSH key as shown below:
```
ssh -i .ssh/id_rsa centos@10.17.3.89
```

### Multiple VMs with cloud-init

`__main__.py`
```python
import pulumi
import pulumi_cloudinit as cloudinit
import pulumi_libvirt as libvirt

number_of_vms = 2

pulumi_network = libvirt.Network("pulumi_network",
addresses=[
    "10.17.3.0/24",
],
dns={
    "enabled": True,
    "local_only": True,
},
dnsmasq_options={},
domain="puluminetwork.local",
mode="nat")

for i in range(number_of_vms):

    pulumi_pool = libvirt.Pool(f"pulumi_pool-{i}",
    type = "dir",
    path = f"/var/lib/libvirt/images/my_pool-{i}"
    )

    pulumi_volume = libvirt.Volume(f"cent10-{i}",
      pool   = pulumi_pool.name,
      source = "/home/hattori/Qcow2/CentOS-Stream-GenericCloud-10-20251027.0.x86_64.qcow2",
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
  - name: centos
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    groups: sudo, wheel
    ssh_authorized_keys:
        - ssh-rsa AAAA...
    password: centos
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

    domain = libvirt.Domain(f"cent10-{i}",
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
        wait_for_lease = True,
      )],
    )

    pulumi.export(f"cent10-{i}", domain.name)
    pulumi.export(f"pulumi_pool-{i}", pulumi_pool.name)
    pulumi.export(f"filesystem-{i}", filesystem.name)
    pulumi.export(f"pulumi_network-{i}", pulumi_network.name)
    pulumi.export("cloud_init_output", cloud_init_config.rendered)
```

### Multiple VMs, no cloud-init

`__main__.py`
```python
import pulumi
import pulumi_libvirt as libvirt

number_of_vms = 2

pulumi_network = libvirt.Network(f"pulumi_network",
    addresses=[
        "10.17.3.0/24",
    ],
    dns={
        "enabled": True,
        "local_only": True,
    },
    dnsmasq_options={},
    domain="puluminetwork.local",
    mode="nat")

for i in range(number_of_vms):

    pulumi_pool = libvirt.Pool(f"pulumi_pool-{i}",
    type = "dir",
    path = f"/var/lib/libvirt/images/my_pool-{i}"
    )

    cent10 = libvirt.Volume(f"cent10-{i}",
    pool   = pulumi_pool.name,
    source = "/home/hattori/Qcow2/CentOS-Stream-GenericCloud-10-20251027.0.x86_64-no-cloud-init.qcow2",
    format = "qcow2",
    )

    # pool size must be larger than the volume size
    filesystem = libvirt.Volume(f"filesystem-{i}",
    base_volume_id = cent10.id,
    pool           = pulumi_pool.name,
    size           = 10*1024*1024*1024 # 10GB
    )

    domain = libvirt.Domain(f"cent10-{i}",
    type = "kvm",
    graphics = libvirt.DomainGraphicsArgs(type="vnc"),
    autostart = False,
    cpu = {
        "mode": "host-passthrough",
    },
    memory = 2048, # 2GB
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
        wait_for_lease = True,
    )],
    )

    pulumi.export(f"cent10-{i}", domain.name)
    pulumi.export(f"pulumi_pool-{i}", pulumi_pool.name)
    pulumi.export(f"filesystem-{i}", filesystem.name)
    pulumi.export(f"pulumi_network", pulumi_network.name)
```

## Erros I saw

### Can't not create a project with pulumi new behind transparent proxy

Try this.
```
pulumi new https://github.com/pulumi/templates/python -s python-dev --force
```

or

```
pulumi new https://github.com/pulumi/templates/python -s python --force
```

### failed to connect: authentication unavailable: no polkit agent available to authenticate action 'org.libvirt.unix.manage':

When issuing pulumi up with non root users, I saw the following errors.
```
$ pulumi up -y
Previewing update (python):
     Type                   Name           Plan       Info
 +   pulumi:pulumi:Stack    test01-python  create
     └─ libvirt:index:Pool  pulumi_pool               1 error

Diagnostics:
  libvirt:index:Pool (pulumi_pool):
    error: failed to connect: authentication unavailable: no polkit agent available to authenticate action 'org.libvirt.unix.manage':

Resources:
    + 1 to create
    1 errored
```

<br>Try this.
```
$ sudo usermod -a -G libvirt <username>
$ newgrp libvirt
```

### error defining libvirt domain: unsupported configuration: spice graphics are not supported with this QEMU:

Add libvirt.DomainGraphicsArgs(type="vnc") in `__main__.py`.
```
domain = libvirt.Domain("cent10",
  graphics = libvirt.DomainGraphicsArgs(type="vnc"),
  type = "kvm",
  ...
```