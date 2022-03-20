# 3. Extra How to(s) and FAQ(s)

**Q. Launch terminal/Open on host on Windows file manager says the drive is not shared?**

A. Open cassowary on Linux, go to **"Folder Mapping"** tab, go to **"Windows->Linux"** sub tab then create a new share for the drive where the file is located then click on mount all.

---

**Q. How do I share my folder on Linux to Windows as local drive ?**

A. Open cassowary on Linux, go to **"Folder Mapping"** tab Goto **"Linux->Windows"** sub tab then click on **Create new file**, give name to share, browse location, choose drive letter then click on create map.

---

**Q. How to launch Windows application that is not listed on guest app by path on Windows?**

A. Run:

```bash
$ python3 -m cassowary -c guest-run -- {path to app and arguments}
```

---

**Q. How do I set links and files on Windows to open on Linux host application?**

A. Set the default app for a file type or default browser to `C:\Program Files\cassowary\hostopen.bat`( if file type 'Launch on host' tab is recommended way to set this up ) 

---

**Q. How do I set to launch a file type on Linux on Windows application?**

A. Most Linux system allow setting default application for file type, create a Application menu entry for the app you want and set default application to the created desktop application.

---

**Q. I setup everything but get a connection error which launching cassowary Linux?**

A. Since cassowary won't launch without a user being logged in, try launching any windows application and click reconnect !

---

**Q. Open on host or open host terminal does not work?**

A. Make sure you have setup background service autostart (logout and login is required after clicking on the setup button). You can also try manually launching background service using:

```bash
$ python -m cassowary -bc
```

---

**Q. Setting file extension on 'Launch on host' does not automatically open it with host application.**

A. Make sure background service shortcut is created and is running, For an extension with app to open it already installed will cause windows to show dialog to choose default app. Select 'Windows script host' on the shown dialog.

---

**Q. New application does not create a taskbar entry.**

A. Disable taskbar application grouping, Also, If you are using v0.6+, try navigating to advanced tab and disable 'Prefer using server to launch applications' this may solve this issue !

---

**Q. There is no internet in VM.**

A. This happens if you have a VPN running on host, try disabling VPN and internet should work on VM !

---

**Q. I have found a bug/issue, have a suggestion, or have questions not answered here!**

A. Feel free to [open an issue here](https://github.com/casualsnek/cassowary/issues)!
