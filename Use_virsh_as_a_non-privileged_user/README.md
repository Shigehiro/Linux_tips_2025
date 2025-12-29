# Use virsh as a non-privileged user

Quick tip.

```
$ cat /etc/centos-release 
CentOS Stream release 10 (Coughlan)
```

## Add the user to the kvm and libvirt groups
```
sudo usermod -aG kvm username
sudo usermod -aG libvirt username
```

## Edit libvirt.conf

### OS-wide configuration
```
$ sudo grep ^uri_default /etc/libvirt/libvirt.conf
uri_default = "qemu:///system"
```

### User configuration
```
$ grep ^uri_default .config/libvirt/libvirt.conf 
uri_default = "qemu:///system"
```