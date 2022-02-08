from PyQt5.QtWidgets import *
from PyQt5 import uic
from .minidialog import MiniDialog
from cassowary.base.cfgvars import cfgvars
from cassowary.base.functions import add_network_share, add_network_map
import os


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
        status, response = add_network_map(client, self.inp_localpath.text(), self.inp_sharename.text(),
                                           self.inp_driveletter.currentText())
        if not status:
            dialog.run(response)
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
        else:
            if on_success is not None:
                on_success()
            self.close()
