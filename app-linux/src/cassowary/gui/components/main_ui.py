import os.path
import socket
from PyQt5.QtWidgets import *
from cassowary.base.functions import *
from cassowary.base.log import get_logger
from cassowary.base.helper import replace_vars, get_windows_cifs_locations, mount_pending, unmount_all, ip_by_vm_name
from .minidialog import MiniDialog
from .sharesandmaps import AddMapDialog, AddShareDialog
from .desktopitemdialog import DesktopItemDialog
from PyQt5 import uic
from cassowary.client import Client
import subprocess

logger = get_logger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.path = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(cfgvars.app_root, "gui", "qtui_files", "main.ui"), self)

        # Create instances of other dialogs
        self.dialog = MiniDialog(self)
        self.new_map_dialog = AddMapDialog()
        self.new_share_dialog = AddShareDialog()

        # Create a client
        self.client = None
        self.__reconnect(no_popup=True)

        # Fix the table columns
        self.__apply_table_props()

        # Add events to button clicks
        self.inp_password.setEchoMode(QLineEdit.Password)
        self.btn_savegconf.clicked.connect(self.__save_vminfo)
        self.btn_newmap.clicked.connect(lambda: self.new_map_dialog.run(self.client, self.populate_mappings))
        self.btn_newshare.clicked.connect(lambda: self.new_share_dialog.run(self.client, self.populate_shares))
        self.btn_mountall.clicked.connect(mount_pending)
        self.btn_ipautodetect.clicked.connect(self.__ip_auto_fill)
        self.btn_unmountall.clicked.connect(unmount_all)
        self.btn_choosemountroot.clicked.connect(self.__set_mount_dir)
        self.btn_newassoc.clicked.connect(self.add_association)
        self.btn_scanapp.clicked.connect(self.populate_applications)
        self.btn_reconnect.clicked.connect(lambda: self.__reconnect())
        self.btn_autofill.clicked.connect(self.__fill_basic_info)
        self.btn_killfreerdp.clicked.connect(lambda: os.popen("killall xfreerdp & killall wlfreerdp"))
        self.btn_fullrdp.clicked.connect(self.__full_rdp)
        self.btn_restart.clicked.connect(lambda: os.popen("virsh reset {}".format(cfgvars.config["vm_name"])))
        self.btn_vmoff.clicked.connect(lambda: os.popen("virsh poweroff {}".format(cfgvars.config["vm_name"])))
        self.btn_closesessions.clicked.connect(lambda: self.client.send_wait_response(["close-sessions"], timeout=4))
        self.btn_serverstop.clicked.connect(lambda: self.client.send_wait_response(["close-server"], timeout=4))
        self.btn_setupautostart.clicked.connect(self.__create_autostart)
        self.btn_createdesktop.clicked.connect(self.__create_menu_item)

        self.main_tabs.currentChanged.connect(self.__tab_changed)
        self.tab_mappings0.currentChanged.connect(self.__mapping_tab_changed)
        self.inp_rdpscale.valueChanged.connect(
            lambda: self.lbl_rdpscalevalue.setText(["100", "140", "180"][self.inp_rdpscale.value()])
        )

        self.populate_general()

    def __create_autostart(self):
        desktop_item = """[Desktop Entry]
Comment=Cassowary Background Service
Encoding=UTF-8
Exec=python -m cassowary -bc
GenericName=cassowary-service
Icon={icon}
Name[en_US]=Cassowary Background Service
Name=Cassowary Background Service
Categories=Utilities
StartupNotify=true
Terminal=false
TerminalOptions=
Type=Application
Version=1.0
""".format(icon=os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "extrares", "cassowary.png"))
        app_dir = os.path.join(os.path.expanduser("~"), ".config", "autostart")
        if not os.path.exists(app_dir):
            os.makedirs(app_dir)
        with open(os.path.join(app_dir, "cassowary_linux_bg_service.desktop"), "w") as df:
            df.write(desktop_item)
        self.dialog.run("Background service autostart script created for current user !")

    def __create_menu_item(self):
        desktop_item = """[Desktop Entry]
Comment=Controls settings for cassowary
Encoding=UTF-8
Exec=python -m cassowary -a
GenericName=cassowary
Icon={icon}
Name[en_US]=Cassowary Linux
Name=Cassowary Linux
Categories=Utilities
StartupNotify=true
Terminal=false
TerminalOptions=
Type=Application
Version=1.0
        """.format(icon=os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "extrares", "cassowary.png"))
        app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "applications")
        if not os.path.exists(app_dir):
            os.makedirs(app_dir)
        with open(os.path.join(app_dir, "cassowary_linux.desktop"), "w") as df:
            df.write(desktop_item)
        self.dialog.run("Application menu item created for current user !")

    @staticmethod
    def __full_rdp():
        command = 'xfreerdp /d:"{domain}" /u:"{user}" /p:"{passd}" /v:{ip} /a:drive,root,/ +auto-reconnect +clipboard '\
                  '/cert-ignore /audio-mode:1 /scale:{scale} /dynamic-resolution /{mflag} {rdflag} 1> /dev/null 2>&1 &'
        multimon_enable = int(os.environ.get("RDP_MULTIMON", cfgvars.config["rdp_multimon"]))
        cmd_final = command.format(
            rdflag=cfgvars.config["rdp_flags"],
            domain=cfgvars.config["winvm_hostname"],
            user=cfgvars.config["winvm_username"],
            passd=cfgvars.config["winvm_password"],
            ip=cfgvars.config["host"],
            scale=cfgvars.config["rdp_scale"],
            mflag="multimon" if multimon_enable else "span"
        )

        os.popen("sh -c '{}' &".format(cmd_final))

    def __apply_table_props(self):
        tbl_map_header = self.tbl_maps.horizontalHeader()
        tbl_map_header.setSectionResizeMode(0, QHeaderView.Stretch)
        tbl_map_header.setSectionResizeMode(1, QHeaderView.Stretch)
        tbl_map_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        tbl_map_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        tbl_shares_header = self.tbl_shares.horizontalHeader()
        tbl_shares_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tbl_shares_header.setSectionResizeMode(1, QHeaderView.Stretch)
        tbl_shares_header.setSectionResizeMode(2, QHeaderView.Stretch)
        tbl_shares_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        tbl_installed_apps_header = self.tbl_installedapps.horizontalHeader()
        tbl_installed_apps_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)

        tbl_associations_header = self.tbl_associations.horizontalHeader()
        tbl_associations_header.setSectionResizeMode(0, QHeaderView.Stretch)

    def __mount_done(self):
        self.dialog.run("Drives should now be mounted !\n If they are not mounted make sure you have correct username/"
                        "password set on 'VM/Guest info' tab")
        self.populate_shares()

    def __set_mount_dir(self):
        dir_path = QFileDialog.getExistingDirectory(None, 'Select mount directory:', "/mnt")
        self.inp_mountroot.setText(os.path.join(dir_path, "casualrdh"))

    def __fill_basic_info(self):
        status, data = get_basic_info(self.client)
        if status:
            self.inp_hostname.setText(data["hostname"])
            self.inp_username.setText(data["username"])
            self.dialog.run("Hostname and Username filled. \n Password must be entered manually !")
        else:
            self.dialog.run(data)

    def __reconnect(self, no_popup=False):

        logger.debug("Tring to start a RDP session for server side component to start !")
        cmd = 'xfreerdp /d:"{domain}" /u:"{user}" /p:"{passd}" /v:"{ip}" +clipboard /a:drive,root,/ ' \
              '+decorations /cert-ignore /audio-mode:1 /scale:100 /dynamic-resolution /span  ' \
              '/wm-class:"cassowaryApp-echo" /app:"echo"'.format( domain=cfgvars.config["winvm_hostname"],
                                                                  user=cfgvars.config["winvm_username"],
                                                                  passd=cfgvars.config["winvm_password"],
                                                                  ip=cfgvars.config["host"]
                                                                  )
        process = subprocess.Popen(["sh", "-c", "{}".format(cmd)])
        logger.debug("Waiting for session startup process to terminate ")
        process.wait()
        logger.debug("Session startup process completed.")
        self.client = Client(cfgvars.config["host"], cfgvars.config["port"])
        try:
            print("Trying to reconnect")
            self.client.init_connection()
            if not no_popup:
                self.dialog.run("Connected to server at {}:{}".format(cfgvars.config["host"],
                                                                      cfgvars.config["port"]))

        except ConnectionRefusedError:
            self.dialog.run("Connection refused by server at '{}':{}".format(cfgvars.config["host"],
                                                                             cfgvars.config["port"]))
        except socket.timeout:
            self.dialog.run("Timed out while connecting to server !\n Make sure server ip is correct and server"
                            " application is running")
        except Exception as e:
            self.dialog.run("Could not connect to server at: {}:{}  \n {}".format(cfgvars.config["host"],
                                                                                  cfgvars.config["port"],
                                                                                  str(e)))

    def __ip_auto_fill(self):
        ip = ip_by_vm_name(self.inp_vmname.text())
        if ip is not None:
            self.inp_vmip.setText(ip)
        else:
            self.dialog.run("Cannot get IP by VM name ! \n Make sure VM name is correct, VM is "
                            "not running as User Session and has active connection"
                            "")

    def __unmount_done(self):
        self.dialog.run("Drives should be unmounted now")
        self.populate_shares()

    def __mapping_tab_changed(self, index):
        if index == 0:
            self.populate_mappings()
        elif index == 1:
            self.populate_shares()

    def __tab_changed(self, index):
        if index == 0:
            self.populate_general()
        elif index == 1:
            self.__mapping_tab_changed(self.tab_mappings0.currentIndex())
        elif index == 2:
            self.populate_applications()
        elif index == 3:
            self.populate_associations()

    def remove_map(self, name):
        status, data = rem_network_map(self.client, name)
        if status:
            self.populate_mappings()
        self.dialog.run(data)

    def remove_share(self, name):
        status, data = rem_network_share(self.client, name)
        if status:
            self.populate_shares()
        self.dialog.run(data)

    def add_association(self):
        file_fmt = self.btn_fileformat.text().strip()
        if file_fmt != "":
            status, data = set_association(self.client, file_fmt)
            if status:
                self.populate_associations()
            self.dialog.run(data)
        else:
            self.dialog.run("Enter a valid file extension !")

    def remove_association(self, name):
        status, data = unset_association(self.client, name)
        if status:
            self.populate_associations()
        self.dialog.run(data)

    def __save_vminfo(self):
        cfgvars.config["winvm_hostname"] = self.inp_hostname.text()
        cfgvars.config["winvm_username"] = self.inp_username.text()
        cfgvars.config["winvm_password"] = self.inp_password.text()
        cfgvars.config["vm_name"] = self.inp_vmname.text()
        cfgvars.config["host"] = self.inp_vmip.text()
        cfgvars.config["rdp_scale"] = int(["100", "140", "180"][self.inp_rdpscale.value()])
        cfgvars.config["rdp_multimon"] = self.inp_rdpmultimon.checkState()
        cfgvars.config["rdp_flags"] = self.inp_rdpflags.text()
        cfgvars.config["term"] = self.inp_defterm.text()
        cfgvars.config["winshare_mount_root"] = self.inp_mountroot.text()
        cfgvars.save_config()
        self.dialog.run("General settings updated !")

    def populate_general(self):
        self.inp_hostname.setText(cfgvars.config["winvm_hostname"])
        self.inp_username.setText(cfgvars.config["winvm_username"])
        self.inp_password.setText(cfgvars.config["winvm_password"])
        self.inp_vmname.setText(cfgvars.config["vm_name"])
        self.inp_vmip.setText(cfgvars.config["host"])
        self.inp_defterm.setText(cfgvars.config["term"])
        self.inp_mountroot.setText(cfgvars.config["winshare_mount_root"])
        self.inp_rdpflags.setText(cfgvars.config["rdp_flags"])
        self.inp_rdpscale.setValue({100: 0, 140: 1, 180: 2}[cfgvars.config["rdp_scale"]])
        self.inp_rdpmultimon.setChecked(bool(cfgvars.config["rdp_multimon"]))

    def populate_mappings(self):
        status, data = get_network_maps(self.client)
        if status:
            while self.tbl_maps.rowCount() > 0:
                self.tbl_maps.removeRow(0)
            for drive_letter in data:
                # Remove button for last column
                btn = QPushButton(self.tbl_maps)
                btn.setText(' Remove ' + drive_letter[0] + ": ")
                btn.clicked.connect(lambda x, letter=data[drive_letter][0]: self.remove_map(drive_letter[0]))
                btn.setMaximumWidth(120)

                # Fill the row
                rows = self.tbl_maps.rowCount()
                self.tbl_maps.insertRow(rows)
                self.tbl_maps.setItem(rows, 0, QTableWidgetItem(data[drive_letter][1]))
                self.tbl_maps.setItem(rows, 1, QTableWidgetItem(data[drive_letter][0]))
                self.tbl_maps.setItem(rows, 2, QTableWidgetItem(drive_letter))
                self.tbl_maps.setCellWidget(rows, 3, btn)
        else:
            self.dialog.run(data)

    def populate_shares(self):
        mounted_shares = dict((value, key) for key, value in get_windows_cifs_locations().items())
        status, data = get_network_shares(self.client)
        if status:
            while self.tbl_shares.rowCount() > 0:
                self.tbl_shares.removeRow(0)
            for drive_letter in data:
                # Remove share buttons in last column
                btn = QPushButton(self.tbl_maps)
                btn.setText(' Remove share ')
                share_name = data[drive_letter][1]
                btn.clicked.connect(lambda x, y=share_name: self.remove_share(y))
                btn.setMaximumWidth(120)
                mount_status = "Not Mounted"
                net_location = replace_vars(data[drive_letter][0])
                if net_location in mounted_shares:
                    mount_status = "Mounted"
                # Fill the row
                rows = self.tbl_shares.rowCount()
                self.tbl_shares.insertRow(rows)
                self.tbl_shares.setItem(rows, 0, QTableWidgetItem(drive_letter))
                self.tbl_shares.setItem(rows, 1, QTableWidgetItem(net_location))
                self.tbl_shares.setItem(rows, 2, QTableWidgetItem(mount_status))
                self.tbl_shares.setCellWidget(rows, 3, btn)
        else:
            self.dialog.run(data)

    def populate_applications(self):

        def _add_btn_clicked(app_name, app_desc, app_path, app_version):
            ico_status, ico_data = get_exe_icon(self.client, app_path)
            create_shortcut_dialog = DesktopItemDialog()
            if ico_status:
                create_shortcut_dialog.run(app_name, app_desc, app_path, app_version, ico_data)
            else:
                self.dialog.run(ico_data)

        status, data = get_installed_apps(self.client)
        if status:
            while self.tbl_installedapps.rowCount() > 0:
                self.tbl_installedapps.removeRow(0)
            for app in data:
                name = app[0].split(":")[0]
                desc = ""
                version = app[2]
                path = app[1]
                parts = app[0].split(":")
                for part in parts[1:len(parts)]:
                    desc = desc + part + ":"
                desc = desc[:-1]

                # Add shortcut button on last column
                btn = QPushButton(self.tbl_maps)
                btn.setText(' Add ')
                btn.clicked.connect(
                    lambda x, a=name, b=desc, c=path, d=version: _add_btn_clicked(a, b, c, d)
                )
                btn.setMaximumWidth(70)

                # Fill the row
                rows = self.tbl_installedapps.rowCount()
                self.tbl_installedapps.insertRow(rows)
                self.tbl_installedapps.setItem(rows, 0, QTableWidgetItem(name))
                self.tbl_installedapps.setItem(rows, 1, QTableWidgetItem(version))
                self.tbl_installedapps.setCellWidget(rows, 2, btn)
        else:
            self.dialog.run(data)

    def populate_associations(self):
        status, data = get_association(self.client)
        if status:
            while self.tbl_associations.rowCount() > 0:
                self.tbl_associations.removeRow(0)
            for file_format in data:
                # Add shortcut button on last column
                btn = QPushButton(self.tbl_maps)
                btn.setText(' Remove ')
                btn.clicked.connect(lambda x, nm=file_format: self.remove_association(nm[1:]))
                btn.setMaximumWidth(100)

                # Fill the row
                rows = self.tbl_installedapps.rowCount()
                self.tbl_associations.insertRow(rows)
                self.tbl_associations.setItem(rows, 0, QTableWidgetItem(file_format))
                self.tbl_associations.setCellWidget(rows, 1, btn)
        else:
            self.dialog.run(data)
