import time
from PyQt5.QtWidgets import *
from PyQt5 import uic
from .minidialog import MiniDialog
from cassowary.base.cfgvars import cfgvars
from cassowary.base.functions import add_network_share, add_network_map
from cassowary.base.helper import wake_base_cmd, get_logger
import os
import subprocess
import re

logging = get_logger(__name__)


class AddMapDialog(QDialog):
    def __init__(self):
        super(AddMapDialog, self).__init__()
        self.path = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(cfgvars.app_root, "gui", "qtui_files", "newmap.ui"), self)
        self.btn_cancel.clicked.connect(self.close)
        self.btn_browse.clicked.connect(self.__select_dir)
        self.inp_localpath.textChanged.connect(
            lambda : self.inp_sharename.setText(
                self.__to_unc_equiv(os.path.abspath(self.inp_localpath.text()))
            )
        )

    def run(self, client, on_success=None):
        self.btn_create.clicked.connect(lambda: self.__add_clicked(client, on_success))
        self.exec_()

    def __to_unc_equiv(self, localpath):
        if cfgvars.config["rdp_share_root"] == "/":
            return "\\\\tsclient\\root{}".format(localpath.replace("/", "\\"))
        else:
            return "\\\\tsclient\\root{}".format(localpath.replace(cfgvars.config["rdp_share_root"], "").replace("/", "\\"))

    def __select_dir(self):
        dir_path = QFileDialog.getExistingDirectory(None, 'Select a folder:', os.path.expanduser("~"))
        self.inp_localpath.setText(dir_path)
        self.inp_sharename.setText(self.__to_unc_equiv(os.path.abspath(dir_path)))

    def __add_clicked(self, client, on_success):
        dialog = MiniDialog(self)
        if not os.path.abspath(self.inp_localpath.text()).startswith(cfgvars.config["rdp_share_root"]):
            dialog.run(
                "Cannot map the directory '{}' !\n "
                "You have set your share root as '{}' and only subdirectories inside this location can be mapped".format(
                    os.path.abspath(self.inp_localpath.text()), cfgvars.config["rdp_share_root"]
                ))
            self.close()
            return None
        if os.path.abspath(self.inp_localpath.text()) == cfgvars.config["rdp_share_root"]:
            dialog.run("The selected directory '' is share root and already available at Z:\\".format(
                cfgvars.config["rdp_share_root"])
            )
            self.close()
            return None
        self.inp_sharename.setText(self.__to_unc_equiv(os.path.abspath(self.inp_localpath.text())))
        process = None
        cmd = wake_base_cmd.format(domain=cfgvars.config["winvm_hostname"],
                                                                    user=cfgvars.config["winvm_username"],
                                                                    passd=cfgvars.config["winvm_password"],
                                                                    ip=cfgvars.config["host"],
                                                                    share_root=cfgvars.config["rdp_share_root"],
                                                                    app="wscript.exe"
                                                                    )+' /app-cmd:\'{app_cmd}\''.format(
            app_cmd = '"C:\\Program Files\\cassowary\\nowindow.vbs" cmd /c "timeout 8"'
        )
        proc = subprocess.check_output(["ps", "auxfww"])
        if len(re.findall(r"freerdp.*\/wm-class:.*cassowaryApp", proc.decode())) < 1:
            logging.debug("No active RDP application, creating one before mapping drive")
            logging.debug("Using commandline: %s", cmd)
            process = subprocess.Popen(["sh", "-c", "{}".format(cmd)], stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
            lo = False
            ts = int(time.time())
            while process.poll() is None and not lo:
                for line in process.stdout:
                    l = line.decode()
                    print(line)
                    if "xf_Pointer" in l:
                        time.sleep(2)
                        logging.debug("Application started, mapping now !")
                        lo = True
                        break
                    elif int(time.time()) - ts > 10:
                        logging.warning("Application is taking too long to start, continuing !")
                        lo = True
                        break
        logging.debug("Sending Request !")
        status, response = add_network_map(client, self.inp_localpath.text(), self.inp_sharename.text(),
                                           self.inp_driveletter.currentText())
        logging.debug("Request complete, killing created application instance")
        if process is not None:
            process.kill()
        if not status:
            dialog.run(response)
            self.close()
        else:
            if on_success is not None:
                on_success()
            self.close()


class AddShareDialog(QDialog):
    def __init__(self):
        super(AddShareDialog, self).__init__()
        uic.loadUi(os.path.join(cfgvars.app_root, "gui", "qtui_files", "newshare.ui"), self)
        self.btn_cancel.clicked.connect(self.close)

    def run(self, client, on_success=None):
        self.btn_createshare.clicked.connect(lambda : self.__add_clicked(client, on_success))
        self.exec_()

    def __add_clicked(self, client, on_success):
        dialog = MiniDialog(self)
        status, response = add_network_share(client, self.inp_driveletter.currentText())
        if not status:
            dialog.run(response)
            self.close()
        else:
            if on_success is not None:
                on_success()
            self.close()
