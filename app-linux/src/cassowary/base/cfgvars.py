import os
import json


class Vars:
    def __init__(self):
        self.app_name = "casualrdh"
        self.config = None
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", self.app_name)
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".cache", self.app_name)
        self.tempdir = os.path.join("/", "tmp", self.app_name)
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        if not os.path.exists(self.tempdir):
            os.makedirs(self.tempdir)
        self.base_config = {
            "host": "192.168.1.1",
            "winvm_username": "",
            "winvm_hostname": "",
            "winvm_password": "Edit It Yourself",
            "vm_name": "",
            "app_session_client": "xfreerdp",
            "full_session_client": "xfreerdp",
            "vm_auto_suspend": 0,
            "vm_suspend_delay": 600,
            "term": "xterm",
            "rdp_scale": 100,
            "rdp_multimon": 0,
            "def_icon": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gui/extrares/cassowary_app.png"),
            "rdp_flags": "",
            "port": 7220,
            "cached_drive_shares": {},
            "winshare_mount_root": os.path.join("/", "mnt", self.app_name),
            "eom": "~~!enm!~~",
            "logfile": os.path.join(self.config_dir, self.app_name + ".log"),
        }
        self.refresh_config()
        self.__check_config()
        self.shared_dict = {}

    def __check_config(self):
        # Preserve config base structure of config file
        changed = False
        for key in self.base_config:
            if key not in self.config:
                self.config[key] = self.base_config[key]
                changed = True
        if changed:
            self.save_config()

    def refresh_config(self):
        if not os.path.isfile(os.path.join(self.config_dir, "config.json")):
            with open(os.path.join(self.config_dir, "config.json"), "w+") as dmf:
                dmf.write(json.dumps(self.base_config))
        with open(os.path.join(self.config_dir, "config.json"), "r") as dmf:
            self.config = json.load(dmf)

    def save_config(self):
        with open(os.path.join(self.config_dir, "config.json"), "w") as dmf:
            dmf.write(json.dumps(self.config))
        self.refresh_config()


cfgvars = Vars()
