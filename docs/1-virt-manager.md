# 1. Setting up Windows vm with virt-manager and KVM
This will help you set up an efficient virtual machine for use with cassowary.

### We start by installing virt-manager and KVM

```
$ sudo pacman -S virt-manager
```

### Making KVM run without root access

```
$ sudo sed -i "s/#user = \"root\"/user = \"$(id -un)\"/g" /etc/libvirt/qemu.conf
$ sudo sed -i "s/#group = \"root\"/group = \"$(id -gn)\"/g" /etc/libvirt/qemu.conf
$ sudo usermod -a -G kvm $(id -un)
$ sudo usermod -a -G libvirt $(id -un)
$ sudo systemctl restart libvirtd
$ sudo ln -s /etc/apparmor.d/usr.sbin.libvirtd /etc/apparmor.d/disable/
```

### Making network available with AppArmor enabled
On some Linux distribution, if AppArmor is enabled, it is necessary to modify the file `/etc/apparmor.d/usr.sbin.dnsmasq` to be able to connect to the network or virt-manager will throw a segmentation fault.

To do that, you will have to add an `r` at the end of line 116, before the comma, so it will be like: `/usr/libexec/libvirt_leaseshelper mr,`.

This can also be done via terminal:

```
$ sudo sed -i "s/\/usr\/libexec\/libvirt_leaseshelper m,/\/usr\/libexec\/libvirt_leaseshelper mr,/g" /etc/apparmor.d/usr.sbin.dnsmasq
```

### Create libvirt.conf
On some Linux distribution is better to create a config file to make sure the default libvirt uri is the system one.

To do this create the folder `~/.config/libvirt/` and inside this folder create the `libvirt.conf` with `uri_default = "qemu:///system"`

```
$ mkdir -p ~/.config/libvirt
$ echo "uri_default = \"qemu:///system\"" >> ~/.config/libvirt/libvirt.conf
```

Now you will need to restart for all the changes to take place.

### Download Windows 10 Pro ISO image and VirtIO Drivers for Windows
We will need Windows 10 Pro, Enterprise or Server to use RDP apps, virtio driver improves the vm performance while having lowest overhead.

- Download Windows 10 iso from: [HERE](https://www.microsoft.com/en-us/software-download/windows10ISO)

- Download latest virtio driver iso images from: [HERE](https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso)

and save them in a convenient location.

### Creating a Virtual Machine
- Open virt-manager from your application menu
- On virt-manager click on **Edit** -> **Preferences**, check **Enable XML editing** then click Close;  
[virt-manager-0](img/virt-manager-0.png)
- On top left of virt-manager click the "**+**" icon, aka **Create a new virtual machine**;
- On the New VM window select **Local Install media** and click Next;  
[virt-manager-1](img/virt-manager-1.png)
- Browse and select the Windows 10 iso you downloaded on install media then click Next again;
- Set the CPU cores (2 recommended), Memory (4096 MB recommended) and Disk Space as per your preferences;  
[virt-manager-2](img/virt-manager-2.png)
[virt-manager-3](img/virt-manager-3.png)
- Give a name to your vm such as `Win10` and check **Customize configuration before install** then click on Finish!;  
[virt-manager-4](img/virt-manager-4.png)
- In the CPU tab make sure **Copy host configuration** is checked;  
[virt-manager-5](img/virt-manager-5.png)
- Goto XML tab of CPU and replace the section:

```
<clock offset='localtime'>
	.......
	.......
</clock>
```

with:

```
<clock offset='localtime'>
  <timer name='hpet' present='yes'/>
  <timer name='hypervclock' present='yes'/>
</clock>
```

- In the Memory tab set the **Curent allocation** to **1024**, so the VM won't use 4GiB of memory directly but it will range from 1GiB to 4GiB;  
[virt-manager-6](img/virt-manager-6.png)
- In the Boot Options tab you could check **Start the virtual machine on host bootup** if you woulòd like the VM to boot automatically at your PC boot;
- In the SATA Disk 1 tab set the **Disk bus** to **VirtIO**;  
[virt-manager-7](img/virt-manager-7.png)
- Move over to NIC section and set **Device Model** to **virtio**;  
[virt-manager-8](img/virt-manager-8.png)
- Click on **Add hardware** at the bottom left, select **Storage** then choose **Select or Create custom storage**; click on **Manage**, browse and select the downloaded virtio-win driver iso. Finally set the device type to **CDROM** and click on Finish;  
[virt-manager-9](img/virt-manager-9.png)
- Click **Begin Installation** on top left;
- Follow the installation instructions for Windows 10 and when choosing a Custom installation you will get no drives to install Windows 10 on. To make the VirtIO drive works you will have to click on **Load Driver**, then choose **OK** and finally select the driver for Windows 10;  
[virt-manager-10](img/virt-manager-10.png)
- After that your drive will show and you can continue like a normal Windows 10 installation;
- After some time you will get to "Let's connect to internet page", click on **I dont have internet** at bottom left and continue with limited setup;
- Set you username and password;
- After you get to Windows 10 desktop open This PC and browse to virtio-win CD drive and install **virtio-win-gt-x64.exe**;
- It's also suggested to install the [spice guest tools](https://www.spice-space.org/download/windows/spice-guest-tools/spice-guest-tools-latest.exe) to also enable copy-paste between host and guest;
- Shut down the VM and on the top left click on **Show virtual hardware button** (second button from the top left of vm window, the blue `i` button);
- Go to Display Spice section and set **Listen Type** to **None**; also check the OpenGL option and click Apply;
- Go to Video QXL section and set **Model** to **VirtIO** and check the 3D acceleration option;
- (if after those two changes all you get is a black screen, revert those changes. This could happen with nVidia graphics card);
- Start the VM by clicking the play button on top left (you may need to click the Monitor icon to show the VM screen ). Login to desktop;
- Open up edge and browse to this page and continue the instructions for installing cassowary.:

---

Note: For better 3D performance you can use VmWare or other virtualization platform, ( The IP autodetection and VM auto suspend only works for libvirt based platforms as of now.

---

**Next guide** -> [Installing cassowary on Windows guest and Linux host](2-cassowary-install.md)
