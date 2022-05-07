import sys
import os
import subprocess
import glob
import traceback
import pywintypes
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
            logger.warning("Failed to get version information for '%s' : %s", path_to_exe, traceback.format_exc())
        return [description, version]
        
    @staticmethod
    def __get_exe_descr(path_to_exe):
        logger.debug("Getting application descriptions for: '{}' ".format(path_to_exe))
        try:
            language, codepage = win32api.GetFileVersionInfo(path_to_exe, '\\VarFileInfo\\Translation')[0]
            stringFileInfo = u'\\StringFileInfo\\%04X%04X\\%s' % (language, codepage, "FileDescription")

            description = win32api.GetFileVersionInfo(path_to_exe, stringFileInfo)
            description = ' '.join(description.split('.'))
        except:
            description = "unknown"
        return description

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
            # Open the directories on App Path -Accessing requires a defined integer, we loop Until we get WinError 259
            for n in range(1000):
                try:
                    app_entry = winreg.OpenKey(app_path_key, winreg.EnumKey(app_path_key, n))
                    path_key = winreg.QueryValueEx(app_entry, None)
                    path = os.path.expandvars(str(path_key[0]))
                    if path not in applications:
                        applications.append(path)
                except Exception as e:
                    if "[WinError 259]" in str(e):
                        break
                    elif "[WinError 2]" in str(e):
                        pass
                    else:
                        logger.error("Exception while scanning for apps ! : "+traceback.format_exc())
                        pass
        return applications
        
    @staticmethod
    def __find_installed_with_info():
        logger.debug("Getting list of installed applications")
        applications = []
        ps_command = "Get-AppxPackage | Select {:s}"
        fields = ["Name", "Version", "InstallLocation"]
        applications_dict = {field: [] for field in fields}
        for field in fields:
            command = ["powershell.exe", ps_command.format(field)]
            p = subprocess.Popen(command, stdout=subprocess.PIPE)
            output, errors = p.communicate()
            if not errors:
                for line in output.decode("utf-8").splitlines():
                    line = line.strip()
                    if line and (not "---" in line) and (not field in line):
                        applications_dict[field].append(line)
            else:
                logger.error("Exception while scanning for apps ! : "+traceback.format_exc())
                return applications

        for i, path in enumerate(applications_dict["InstallLocation"]):
            executables = glob.glob(path + "\\**\\*.exe", recursive=True)
            n = len(executables)
            if n == 0:
                executable = None
            elif n > 1:
                executable = None
                executable_size = 0 
                for file in executables:
                    size = os.path.getsize(file)
                    if size > executable_size:
                        executable = file
                        executable_size = size
            else:
                executable = executables[0]
                
            if executable is not None and not "SystemApps" in executable:
                if applications_dict["Name"][i] is None:
                    name = os.basename(executable).split('.')[0]
                    name = name[0].upper() + name[1:]
                else:
                    name = ' '.join(applications_dict["Name"][i].split('.'))
                applications.append([name, executable, applications_dict["Version"][i]])
                
        return applications

    def run_cmd(self, cmd):
        if cmd[0] == "get-installed-apps":
            installed_apps = []
            # app_name: [path_to_exe, version, icon ]
            if sys.getwindowsversion().major < 10:
                apps = self.__find_installed()
                for app in apps:
                    app_info = self.__get_exe_info(app)
                    # NOTE: app_info[0] is app icon remove it from the returned data
                    installed_apps.append([app_info[0], app, app_info[1]])
                    # [description, path, version]
            else:
                apps_with_info = self.__find_installed_with_info()
                for app_with_info in apps_with_info:
                    app_descr = self.__get_exe_descr(app_with_info[1])
                    if app_descr is not None and app_descr != "unknown":
                        app_with_info[0] = app_descr
                    installed_apps.append(app_with_info)
                    # [description, path, version]
            return True, installed_apps
        elif cmd[0] == "get-exe-icon":
            return True, self.__get_exe_image(cmd[1])
        else:
            return False, None
