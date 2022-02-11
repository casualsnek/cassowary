import time
import traceback
import threading
import libvirt
from PyQt5.QtWidgets import *
from PyQt5 import uic
from cassowary.base.cfgvars import cfgvars
from cassowary.base.log import get_logger
import os

logging = get_logger(__name__)


class StartDg(QDialog):
    def __init__(self, parent=None):
        super(StartDg, self).__init__(parent)
        self.path = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(cfgvars.app_root, "gui", "qtui_files", "vmstart.ui"), self)
        self.lb_msg.setText("The VM '{}' is not running. Do you want to start the vm now ?\n".format(cfgvars.config["vm_name"]))
        self.btn_startvm.clicked.connect(self.bg_st)
        self.btn_cancel.clicked.connect(self.close)

    def bg_st(self):
        stt = threading.Thread(target=self.wait_vm)
        stt.start()

    def wait_vm(self):
        self.btn_startvm.hide()
        self.btn_cancel.setEnabled(False)
        if cfgvars.config["vm_name"].strip() != "":
            logging.debug("Using VM")
            try:
                conn = libvirt.open(cfgvars.config["libvirt_uri"])
                if conn is not None:
                    self.lb_msg.setText(self.lb_msg.text() + "=> Connected to libvirt !\n")
                    dom = conn.lookupByName(cfgvars.config["vm_name"])
                    self.lb_msg.setText(self.lb_msg.text() + "=> VM Found\n")
                    if dom.info()[0] == 5:
                        logging.debug("VM was found and is turned off")
                        self.lb_msg.setText(self.lb_msg.text() + "=> Starting the vm \n")
                        dom.create()
                        logging.debug("Called libvirt to start the VM")
                        self.lb_msg.setText(self.lb_msg.text() + "=> Waiting for VM networking to be active !\n")
                        vm_ip = None
                        logging.debug("Waiting for VM to get valid IP address\n")
                        while vm_ip is None:
                            interfaces = dom.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)
                            if interfaces is not None:
                                for interface in interfaces:
                                    try:
                                        vm_ip = interfaces[interface]["addrs"][0]["addr"]
                                    except (KeyError, IndexError) as e:
                                        pass
                            time.sleep(1)
                        self.lb_msg.setText(self.lb_msg.text() + "=> Got VM IP address : "+ vm_ip)
                        logging.debug("VM has ip '%s' now !", vm_ip)
                    conn.close()
            except libvirt.libvirtError:
                logging.error("Cannot start VM. : %s", traceback.format_exc())
        self.close()

    def run(self):
        self.exec_()
