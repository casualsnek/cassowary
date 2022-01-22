# <img src="app-linux/src/cassowary/gui/extrares/cassowary.svg" alt="Logo" width="200"/>  Cassowary 

[![Visits Badge](https://badges.pufler.dev/visits/casualsnek/cassowary)](https://github.com/casualsnek)

With cassowary you can run windows vm and use windows applications on linux as if they are native applications by using freerdp and remote apps as base.

**If you prefer a setup guide video instead of wall of text :  [Click Here](https://www.youtube.com/watch?v=ftq-c_VgmK0)**

Give a star ⭐ or follow if you find this project useful

## Cassowary supports:
 - Running windows application as if they are native application
 - Opening files from linux host directly on windows applications
 - Using linux apps to open files that are on windows vm
 - Easily accessing guest filesystem from host
 - Easily access host filesystem from windows
 - Easy to use configuration utility
- Creating application launcher for windows application easily

## This README consists of instructions for:
1. [Setting up Windows VM with virt-manager](docs/1-virt-manager.md)
2. [Installing cassowary on Windows guest and Linux host](docs/2-cassowary-install.md)
3. [Extra How to's and FAQ](docs/3-faq.md)
4. Building cassowary from source
5. How can i help?

# 4. Building cassowary from source
Install wine first in order to build windows application on linux, internet is required to download python binary for setup 

```
$ git clone https:// github.com/casualsnek/cassowary
$ cd cassowary
$ ./buildall.sh
```

This will result a dist folder inside app-linux which contains the installed wheel file
also a bin folder will be created in app-windows containing the setup files

# 5. How can i help ?
- Improve the README.md
- Report bugs or submit patches
- Maybe video instructions for new users, or add screenshots with the setup instructions
- Maybe donate so i can spend some more time maintaining it !
