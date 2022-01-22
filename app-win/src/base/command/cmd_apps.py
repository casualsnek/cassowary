import os
import traceback
import winreg
import win32api
from base64 import b64encode
from icoextract import IconExtractor
from base.log import get_logger


logger = get_logger(__name__)


class ApplicationData:
    def __init__(self):
        self.CMDS = ["get-installed-apps", "get-exe-icon"]
        self.NAME = "installedappcommands"
        self.DESC = "Provides installed app information from registry including app icons"

    @staticmethod
    def __get_exe_info(path_to_exe):
        logger.debug("Getting application descriptions for: '{}' ".format(path_to_exe))
        try:
            language, codepage = win32api.GetFileVersionInfo(path_to_exe, '\\VarFileInfo\\Translation')[0]
            stringFileInfo = u'\\StringFileInfo\\%04X%04X\\%s' % (language, codepage, "FileDescription")
            stringVersion = u'\\StringFileInfo\\%04X%04X\\%s' % (language, codepage, "FileVersion")

            description = win32api.GetFileVersionInfo(path_to_exe, stringFileInfo)
            version = win32api.GetFileVersionInfo(path_to_exe, stringVersion)
        except:
            description = "unknown"
            version = "unknown"
        # TODO: Remove None and use different function to get app icons !
        return [description, version]

    @staticmethod
    def __get_exe_image(exe_path):
        img_str = ""
        try:
            extractor = IconExtractor(exe_path)
            icon = extractor.get_icon()
            img_str = b64encode(icon.getvalue()).decode()
        except:
            img_str = ""
        return img_str
    @staticmethod
    def __find_installed():
        logger.debug("Getting list of installed applications")
        applications = []
        for installation_mode in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            # Open HKLM and HKCU and look for installed applications
            try:
                registry = winreg.ConnectRegistry(None, installation_mode)
                app_path_key = winreg.OpenKey(registry, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
            except FileNotFoundError:
                # If the Key does not exist instead of throwing an exception safely ignore it
                pass
            # Open the directories on App Path -Accessing requires defined integer, so we loop Until we get WinError 259
            for n in range(1000):
                try:
                    app_entry = winreg.OpenKey(app_path_key, winreg.EnumKey(app_path_key, n))
                    path_key = winreg.QueryValueEx(app_entry, None)
                    path = os.path.expandvars(str(path_key[0]))
                    if path not in applications:
                        applications.append(path)
                except Exception as e:
                    if str(e) == "[WinError 259]":
                        break
                    elif str(e) == "[WinError 2]":
                        pass
                    else:
                        logger.error("Exception while scanning for apps ! : "+traceback.format_exc())
                        pass
        return applications

    def run_cmd(self, cmd):
        if cmd[0] == "get-installed-apps":
            installed_apps = []
            # app_name: [path_to_exe, version, icon ]
            apps = self.__find_installed()
            for app in apps:
                app_info = self.__get_exe_info(app)
                # NOTE: app_info[0] is app icon remove it from the returned data
                installed_apps.append([app_info[0], app, app_info[1]])
                # [description, path, version]
            return True, installed_apps
        elif cmd[0] == "get-exe-icon":
            return True, self.__get_exe_image(cmd[1])
        else:
            return False, None