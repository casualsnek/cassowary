from .minidialog import MiniDialog
from cassowary.base.cfgvars import cfgvars
from cassowary.base.helper import create_desktop_entry
from PyQt5.QtWidgets import *
from PyQt5 import uic
import base64
import os


class DesktopItemDialog(QDialog):
    def __init__(self):
        super(DesktopItemDialog, self).__init__()
        uic.loadUi(os.path.join(cfgvars.app_root, "gui", "qtui_files", "desktopcreate.ui"), self)
        self.btn_dismiss.clicked.connect(self.close)
        self.dialog = MiniDialog(self)

    def run(self, name, description, path, version, icon=None):
        # Save the icon
        filename = "cassowary" + ''.join(e for e in name if e.isalnum())
        icon_path = os.path.join(cfgvars.cache_dir, filename + ".ico")
        try:
            if not icon == "":
                with open(icon_path, "wb") as ico_file:
                    ico_file.write(base64.b64decode(icon))
            else:
                icon_path = cfgvars.config["def_icon"]
        except KeyError:
            pass
        self.inp_name.setText(name)
        self.inp_icon.setText(icon_path)
        self.inp_description.setText(description + " (cassowary remote application)")
        self.inp_comment.setText("'{}' version '{}'".format(name, version))
        self.inp_command.setText("python3 -m cassowary -c guest-run -- '{}' %u".format(
            path.replace("\\", "\\\\").replace("'", "").replace("\"", ""))
        )
        # Not using pixmap for now, just use css border-image
        self.lb_appicon.setStyleSheet("border-image: url('{}')".format(icon_path))
        self.btn_save.clicked.connect(lambda: self.__save_desktop(filename))
        self.exec_()

    def __save_desktop(self):
        self.dialog.run(create_desktop_entry(
            self.inp_name.text(), self.inp_comment.text(), self.inp_command.text(),
            self.inp_description.text(), self.inp_icon.text(), self.inp_categories.text()
        ))
        self.close()
