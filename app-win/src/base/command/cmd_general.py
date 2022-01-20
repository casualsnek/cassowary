import os
from base.log import get_logger
import sys

logger = get_logger(__name__)


class CmdGeneral:
    def __init__(self):
        self.CMDS = ["get-basic-info", "close-server", "close-sessions"]
        self.NAME = "generalcommands"
        self.DESC = "Provides simple commands to get information"

    @staticmethod
    def __get_names():
        return True, {"username": os.environ["USERNAME"], "hostname": os.environ["COMPUTERNAME"]}

    def run_cmd(self, cmd):
        if cmd[0] == "get-basic-info":
            status, data = self.__get_names()
            return True, data
        elif cmd[0] == "close-server":
            sys.exit(0)
        elif cmd[0] == "close-sessions":
            os.popen("logout")
            return False, "Error"
        else:
            return False, None