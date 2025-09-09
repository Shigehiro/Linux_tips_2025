# Run ESXi8 under KVM (Nested)

## KVM host information

```
$ cat /etc/centos-release ;uname -r
CentOS Stream release 10 (Coughlan)
6.12.0-126.el10.x86_64

$ /usr/libexec/qemu-kvm --version
QEMU emulator version 10.0.0 (qemu-kvm-10.0.0-12.el10)
Copyright (c) 2003-2025 Fabrice Bellard and the QEMU Project developers
```

## Wlakthrough logs

Enable nested. You need to reboot the OS to reflect that.
```
$ grep nested /etc/modprobe.d/kvm.conf |grep -v ^#
options kvm_intel nested=1
```

Prepare the ISO and install ESXi8.
```shell
sudo virt-install \
--virt-type=kvm \
--name=vmware-esxi8 \
--ram 16384 \
--vcpus=8 \
--hvm \
--cdrom /var/lib/libvirt/images/VMware-VMvisor-Installer-8.0U3e-24677879.x86_64.iso \
--network network:default,model=e1000e \
--graphics vnc \
--disk path=/var/lib/libvirt/images/esxi-vol01.qcow2,size=32,sparse=true,bus=sata,format=qcow2 \
--disk path=/var/lib/libvirt/images/esxi-vol02,size=32,sparse=true,bus=sata,format=qcow2 \
--boot cdrom,hd \
--noautoconsole \
--cpu host-passthrough \
--os-variant linux2024
```

Proceed with the installation using virt-manager and/or Cockpit.
```
[root@localhost:~] vmware -v
VMware ESXi 8.0.3 build-24677879
```

