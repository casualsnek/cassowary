import os
from base.log import get_logger
import sys

logger = get_logger(__name__)


class CmdGeneral:
    def __init__(self):
        self.CMDS = ["get-basic-info", "close-server", "close-sessions", "run-app"]
        self.NAME = "generalcommands"
        self.DESC = "Provides simple commands to get information/run applications"

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
        elif cmd[0] == "run-app":
            command_str = ''
            for i in range(1, len(cmd)):
                if " " in cmd[i]:
                    command_str = command_str+'"{}" '.format(cmd[i])
                else:
                    command_str = command_str+cmd[i]+' '
            os.system(command_str)
            return True, "App with commandline executed: '{}' ".format(command_str)
        else:
            return False, None
