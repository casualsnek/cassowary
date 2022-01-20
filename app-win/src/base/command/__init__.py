from .cmd_dirs import DriveShareHelper
from .cmd_apps import ApplicationData
from .cmd_asso import FileAssociation
from .cmd_general import CmdGeneral

from ..helper import cfgvars


def register_all():
    cfgvars.register_cmd(DriveShareHelper)
    cfgvars.register_cmd(ApplicationData)
    cfgvars.register_cmd(FileAssociation)
    cfgvars.register_cmd(CmdGeneral)
    return True
