from PyQt5.QtWidgets import *
from PyQt5 import uic
from base.cfgvars import cfgvars
import os


class MiniDialog(QDialog):
    def __init__(self, parent=None):
        super(MiniDialog, self).__init__(parent)
        self.path = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(cfgvars.app_root, "gui", "qtui_files", "notice.ui"), self)
        self.btn_close.clicked.connect(self.close)

    def run(self, content):
        self.lb_main.setText(str(content))
        self.exec_()