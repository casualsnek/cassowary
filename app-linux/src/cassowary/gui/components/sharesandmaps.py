from PyQt5.QtWidgets import *
from PyQt5 import uic
from .minidialog import MiniDialog
from base.cfgvars import cfgvars
from base.functions import add_network_share, add_network_map
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
                "\\\\tsclient\\root{}".format(os.path.abspath(self.inp_localpath.text()).replace("/", "\\"))
            )
        )
        self.dialog = MiniDialog(self)

    def run(self, client, on_success=None):
        self.btn_create.clicked.connect(lambda : self.__add_clicked(client, on_success))
        self.exec_()

    def __select_dir(self):
        dir_path = QFileDialog.getExistingDirectory(None, 'Select a folder:', os.path.expanduser("~"))
        self.inp_localpath.setText(dir_path)
        self.inp_sharename.setText("\\\\tsclient\\root{}".format(os.path.abspath(dir_path).replace("/", "\\")))

    def __add_clicked(self, client, on_success):
        inp_sharename = self.inp_sharename.setText("\\\\tsclient\\root{}".format(
            os.path.abspath(self.inp_localpath.text()).replace("/", "\\"))
        )
        status, response = add_network_map(client, self.inp_localpath.text(), self.inp_sharename.text(),
                                           self.inp_driveletter.currentText())
        if not status:
            self.dialog.run(response)
        else:
            if on_success is not None:
                on_success()
            self.close()


class AddShareDialog(QDialog):
    def __init__(self):
        super(AddShareDialog, self).__init__()
        uic.loadUi(os.path.join(cfgvars.app_root, "gui", "qtui_files", "newshare.ui"), self)
        self.btn_cancel.clicked.connect(self.close)
        self.dialog = MiniDialog(self)

    def run(self, client, on_success=None):
        self.btn_createshare.clicked.connect(lambda : self.__add_clicked(client, on_success))
        self.exec_()

    def __add_clicked(self, client, on_success):
        status, response = add_network_share(client, self.inp_driveletter.currentText())
        if not status:
            self.dialog.run(response)
        else:
            if on_success is not None:
                on_success()
            self.close()