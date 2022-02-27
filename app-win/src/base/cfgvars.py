import os
import json


class Vars:
    def __init__(self):
        self.app_name = "casualrdh"
        self.config = None
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", self.app_name)
        self.tempdir = os.path.join(os.path.expandvars("%TEMP%"), self.app_name)
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        if not os.path.exists(self.tempdir):
            os.makedirs(self.tempdir)
        self.base_config = {
            "remembered_maps": {},
            "remembered_assocs": {},
            "port": 7220,
            "eom": "~~!enm!~~",
            "logfile": os.path.join(self.config_dir, self.app_name + ".log"),
            "host": "0.0.0.0",
            "tracked_installations": [],
            "assoc_ftype": "casualhXDGO",
            "xdg_open_handle": "wscript.exe \"C:\\Program Files\\cassowary\\cassowary_nw.vbs\" -c xdg-open -- \"%1\"",
        }
        self.refresh_config()
        self.__check_config()
        self.cmd_queue_host_only = []
        self.cmd_host_only_responses = {}
        self.cmd_host_only_ids = []
        self.commands = {}
        self.commands_handlers = {}
        self.shared_dict = {}

    def register_cmd(self, runner_class):
        obj = runner_class()
        if obj.NAME not in self.commands_handlers:
            self.commands_handlers[obj.NAME] = obj
        else:
            print("Conflicting name '{}', Used by: {} AND {}".format(
                obj.NAME,
                self.commands_handlers[obj.NAME].DESC,
                runner_class.DESC
            ))
            exit(1)
        for command in obj.CMDS:
            if command not in self.commands:
                self.commands[command] = obj.NAME
            else:
                print("Command: '{}' already associated to-> {} : {}".format(
                    command,
                    self.commands_handlers[self.commands[command]].DESC,
                    obj.DESC
                ))
                exit(1)
        return True
        
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
