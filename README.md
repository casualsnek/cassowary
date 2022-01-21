# <img src="app-linux/src/cassowary/gui/extrares/cassowary.svg" alt="Logo" width="200"/>  Cassowary 


[![Visits Badge](https://badges.pufler.dev/visits/casualsnek/cassowary)](https://github.com/casualsnek)

With cassowary you can run windows vm and use windows applications on linux as if they are native applications by using freerdp and remote apps as base.

**If you prefer a setup guide video instead of wall of text :  [Click Here](https://www.youtube.com/watch?v=ftq-c_VgmK0)**

Give a star ⭐ or follow if you find this project useful

#### Cassowary supports
 - Running windows application as if they are native application
 - Opening files from linux host directly on windows applications
 - Using linux apps to open files that are on windows vm
 - Easily accessing guest filesystem from host
 - Easily access host filesystem from windows
 - Easy to use configuration utility
- Creating application launcher for windows application easily

#### This README consists of instructions for
- Installing up cassowary on linux host
- Setting up Windows vm with virt-manager
- Installing up cassowary on windows and linux
- Building cassowary from source
- Extra How to's and FAQ
- How can i help ?
## Installing cassowary on Linux host
Here we will be using arch linux, you can easily find equivalent commands for your linux distro
- Goto the release page and download latest .whl file
- Open terminal on the location where you downloaded the .whl file
- Install python3 and dependencies by running following commands on terminal
```
$ sudo pacman -S python3 python-pip freerdp
$ pip3 install PyQt5
```
- Install the downloaded .whl file by running
```
$ pip install cassowary*
```
- Launch cassowary configuration utility with ```$ python3 -m cassowary -a```
- Head over to misc tab and click on 'Setup Autostart' and 'Create' this will bring cassowary to your application menu and setup background service autostart

## Setting up Windows vm with virt-manager and KVM
This will help you set up an efficient virtual machine for use with cassowary.

#### We start by installing virt-manager and KVM
```
$ sudo pacman -S virt-manager
```

#### Making KVM run without root access
```
$ sudo sed -i "s/#user = "root"/user = "$(id -un)"/g" /etc/libvirt/qemu.conf
$ sudo sed -i "s/#group = "root"/group = "$(id -gn)"/g" /etc/libvirt/qemu.conf
$ sudo usermod -a -G kvm $(id -un)
$ sudo usermod -a -G libvirt $(id -un)
$ sudo systemctl restart libvirtd
$ sudo ln -s /etc/apparmor.d/usr.sbin.libvirtd /etc/apparmor.d/disable/
```
You may need to restart for changes to take place and get current user added to group properly

#### Download Windows 10 pro ISO image and VirtIO Drivers for windows
We will need Windows 10 Pro, Enterprise or Server to use RDP apps, virtio driver improves the vm performance while having lowest overhead

Download windows 10 iso from [HERE](https://www.microsoft.com/en-us/software-download/windows10ISO)

Download latest virtio driver iso images from: [HERE](https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso)

and save them in convenient location

#### Creating Virtual Machine
- Open virt-manager from your application menu
- On virt-manager click on 'Edit'->'Preferences' and enable XML editing then click close
- On top left of virt-manager click the '+' icon
- On the New VM window select Local Install media and click Next
- Browse and select the Windows 10 iso you downloaded on install media then click next again
- Set the CPU cores ( 2 recommended ), Memory ( 4096 MB recommended ) and Disk Space as per your preferences
- Give a name to your vm such as : win10 and check the Customize configuration before install then click on finish !
- On the next window make sure 'Copy host configuration' is checked
- Goto XML tab of CPU and replace the section
```
<clock offset='localtime'>
	.......
	.......
</clock>
```
with 
```
<clock offset='localtime'>
  <timer name='hpet' present='yes'/>
  <timer name='hypervclock' present='yes'/>
</clock>
```

- Move over to NIC section and set 'Device Model' to 'virtio'
- Click on Add hardware at the bottom left, Select Storage the Choose 'Select or Create custom storage', Click on Manage and browse and select the downloaded virtio-win driver iso, Set the device type to CDROM
- Click Finish
- Click Begin Installation on top left
- Follow the installation instructions for windows 10 and choose Windows 10 Pro as the edition to install
- After some time you will get to 'Let's connect to internet page', click on 'I dont have internet at bottom left' and continue with limited setup
- Set you username and password
- After you get to windows 10 desktop open This pc and browse to virtio-win CD drive and double click on virtio-win-gt-x64.exe
- Shut down the VM and on the top left click on show 'Show virtual hardware button' ( second button from the top left of vm window the `i` button )
- Go to Display Spice section and Set listen type to None also check the OpenGL option and click Apply
- Go to Video QXL section and set Model to Virtio and check the 3D acceleration option
- Start the VM by clicking the play button on top left. ( You may need to click the Monitor icon to show the VM screen ) and login to desktop
- Open up edge and browse to this page and continue the instructions for installing cassowary


## Installing up cassowary on windows and linux
#### On Windows 
- Open Settings and Click on System and Scroll to bottom and click on Remote desktop then Click on Enable Remote Desktop and click confirm !
- Open this page and download latest .zip from the release page
- Extract the downloaded zip file
- Double click on setup.bat located on extracted directory
- Logout and login again to windows session
- After you have logged in continue the instructions below
#### On Linux
- Launch cassowary linux using your application menu or run ```$ python3 -m cassowary -a ```
- Enter the VM name from the vm setup step in this case 'win10'
- Click on 'Save changes' and then on 'Autodetect', this should automatically fill up the vm IP
- Click 'Save changes' again then click 'Autofill host/username' then enter the password you set during the windows setup. Then click 'Save changes'...again
- Now goto 'Guest app' tab and create shortcut for any application you want

Now you can find application on your application menu which you can use to launch apps easily
You can explore other commandline usage of cassowary by running ```$ python -m cassowary -h```

## Building cassowary from source
Install wine first in order to build windows application on linux, internet is required to download python binary for setup 
```
$ git clone https:// github.com/casualsnek/cassowary
$ cd cassowary
$ ./buildall.sh
```
This will result a dist folder inside app-linux which contains the installed wheel file
also a bin folder will be created in app-windows containing the setup files


## Extra How to's and FAQ
##### Q. Launch terminal/Open on host on windows file manager says drive is not shared ?
A. Open cassowary on linux, goto 'Folder Mapping tab' Goto 'Windows->Linux' sub tab then create a new share for drive where the file is located then click on mount all

##### Q. How to i share my folder on linux to windows as local drive ?
A. Open cassowary on linux, goto 'Folder Mapping tab' Goto 'Linux->Windows'
sub tab then click on Create new file, Give name to share, browse location, choose drive letter then click on create map

##### Q. How to launch windows application that is not listed on guest app by path on windows ?
A. Run ```python3 -m cassowary cassowary -c guest-run -- { path to app and arguments } ```

##### Q. How do i set links and files on windows to open on linux host application ?
A. Set the default app for a file type or default browser to 'C:\Program Files\cassowary\hostopen.bat'

##### Q. How do i set to launch a file type on linux on windows application ?
A. Most linux system allow setting default application for file type, create a Application menu entry for the app you want and set default application to the created desktop application.

##### Q. I setup every thing but get connection error which launching cassowary linux ?
A. Since cassowary wont launch without a user being logged in, try launching any windows application and click reconnect !

##### Q. Open on host or open host terminal does not work ?
A. Make sure you have setup background service autostart ( logout and login is required after clicking on setup button ), You can also try manually launching background service using ```$ python -m cassowary -bc ```

##### Q. I have found a bug/issue, have a suggestion or i have questions not answered here !
A. Feel free to open an issue here ! 

## How can i help ?
- Improve the README.md
- Report bugs or submit patches
- Maybe video instructions for new users, or add screenshots with the setup instructions
- Maybe donate so i can spend some more time maintaining it !
