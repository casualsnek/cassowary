# 3. Extra How to's and FAQ

**Q. Launch terminal/Open on host on Windows file manager says drive is not shared?**

A. Open cassowary on linux, go to **"Folder Mapping"** tab, go to **"Windows->Linux"** sub tab then create a new share for drive where the file is located then click on mount all.

---

**Q. How do I share my folder on Linux to Windows as local drive ?**

A. Open cassowary on linux, go to **"Folder Mapping"** tab Goto **"Linux->Windows"** sub tab then click on **Create new file**, give name to share, browse location, choose drive letter then click on create map.

---

**Q. How to launch Windows application that is not listed on guest app by path on Windows?**

A. Run:

```
$ python3 -m cassowary cassowary -c guest-run --{path to app and arguments}
```

---

**Q. How do I set links and files on Windows to open on Linux host application?**

A. Set the default app for a file type or default browser to `C:\Program Files\cassowary\hostopen.bat`

---

**Q. How do I set to launch a file type on Linux on Windows application?**

A. Most Linux system allow setting default application for file type, create a Application menu entry for the app you want and set default application to the created desktop application.

---

**Q. I setup every thing but get connection error which launching cassowary Linux?**

A. Since cassowary wont launch without a user being logged in, try launching any windows application and click reconnect !

---

**Q. Open on host or open host terminal does not work?**

A. Make sure you have setup background service autostart (logout and login is required after clicking on setup button). You can also try manually launching background service using:

```
$ python -m cassowary -bc
```
---

**Q. I have found a bug/issue, have a suggestion or I have questions not answered here!**

A. Feel free to [open an issue here](https://github.com/casualsnek/cassowary/issues)!
