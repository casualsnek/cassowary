import os
import re
from ..helper import uac_cmd_exec
from ..cfgvars import cfgvars
from base.log import get_logger


logger = get_logger(__name__)


class DriveShareHelper:
    def __init__(self):
        self.CMDS = ["add-drive-share", "get-drive-shares", "rem-drive-share", "add-network-map", "get-network-map",
                     "rem-network-map"]
        self.NAME = "dircommands"
        self.DESC = "Share Windows drives to network to access them from linux"
        # Check if Z is shared
        if os.path.exists("\\\\tsclient\\root"):
            active_maps = self.__get_active_network_maps()
            if "Z:\\" not in active_maps:
                # No map for root, create one now
                cmd_out = uac_cmd_exec("net use Z: \\\\tsclient\\root /persistent:Yes", noadmin=True, timeout=8)
                if "command completed successfully" in cmd_out:
                    print("Host root is now mounted as Z :) ")
        else:
            logger.debug("Looks like this is not a RDP session, share for root folder not found")

    @staticmethod
    def __get_active_network_maps():
        logger.debug("Getting active network location mapping using net use")
        cmd_out = uac_cmd_exec("net use", noadmin=True)
        if cmd_out is None:
            logger.error("Failed to get output of net share, command error")
            return False, "Failed to get output of command 'net share' "
        else:
            cmd_out = cmd_out.split("\n")
        i = 6
        active_maps = {}
        position_local = cmd_out[3].find("Local")
        position_remote = cmd_out[3].find("Remote")
        position_network = cmd_out[3].find("Network")
        while i < len(cmd_out) - 3:
            status = cmd_out[i][0:position_local].strip()
            local = cmd_out[i][position_local:position_remote].strip()
            remote = cmd_out[i][position_remote:position_network].strip()
            active_maps[local.upper() + "\\"] = [remote, status]
            i = i + 1
        return active_maps

    def __add_new_map(self, remote_path, network_location, drive_letter):
        drive_letter = drive_letter[0].upper()
        logger.debug("Attempting to add mapping from '%s' to letter '%s' resolving to host path '%s'",
                     network_location, drive_letter, remote_path)
        active_maps = self.__get_active_network_maps()
        if drive_letter == "Z":
            return False, "Drive letter 'Z' is reserved for root '/' "
        if network_location.endswith("\\"):
            network_location = network_location[:-1]
        if len(remote_path) > 1 and remote_path.endswith("/"):
            remote_path = remote_path[:-1]
        if not drive_letter + ":\\" in active_maps:
            # Drive letter is not used, good to go
            cmd_out = uac_cmd_exec(
                "net use {drive_letter}: {network_location} /persistent:Yes".format(drive_letter=drive_letter,
                                                                                    network_location=network_location),
                noadmin=True)
            if "command completed successfully" in cmd_out:
                cfgvars.refresh_config()
                # Keep a record of remote host path for this map
                cfgvars.config["remembered_maps"][drive_letter + ":\\"] = [network_location, remote_path]
                cfgvars.save_config()
                logger.debug("Added mapping from '%s' to letter '%s' resolving to host path '%s'",network_location,
                             drive_letter, remote_path)
                return True, "Host path '{}' is now mapped to drive '{}' ".format(remote_path, drive_letter)
            elif "network path was not found" in cmd_out:
                logger.warning("The network path (%s) to map was not found", network_location)
                return False, "The network path to map was not found"
            else:
                logger.error("Unknown error while trying to map to drive: '%s'", cmd_out)
                return False, "Unknown error while trying to map to drive '{}'".format(cmd_out)
        else:
            logger.warning("Map not added, drive letter already in use")
            return False, "The drive letter is already in use"

    @staticmethod
    def __remove_map(name):
        logger.debug("Attempting to remove network mapping of : %s", name)
        if not name.startswith("\\\\"):
            name = name[0].upper() + ":"
        cmd_out = uac_cmd_exec("net use {name} /delete".format(name=name), noadmin=True)
        if "was deleted successfully" in cmd_out:
            # Remove from remembered maps if it is there
            logger.debug("Trying to remove location'%s' from remembered map", name)
            if not name.startswith("\\\\"):
                if name + "\\" in cfgvars.config["remembered_maps"]:
                    # Remove it
                    cfgvars.config["remembered_maps"].pop(name + "\\")
                    logger.debug("Removed mapping")
            else:
                for letter in cfgvars.config["remembered_maps"]:
                    if cfgvars.config["remembered_maps"][letter][0] == name:
                        # Remove it
                        logger.debug("Removed mapping")
                        cfgvars.config["remembered_maps"].pop(letter)
            # Save changes
            cfgvars.save_config()
            logger.debug("Network location Map to '%s' drive removed", name)
            return True, "Network location Map to '{}' drive removed".format(name)
        elif "network connection could not be found" in cmd_out:
            logger.warning("Not removed network location Map to '%s' does not exist", name)
            return False, "No map to '{}' drive exists !".format(name)

    @staticmethod
    def __get_shared_drives(no_hostname=False):
        # This should return the current network share location of drives
        #           <local_drive> : <network_share_name>
        #
        logger.debug("Getting shared local drives using net share")
        cmd_out = uac_cmd_exec("net share", noadmin=True)
        if cmd_out is None:
            logger.error("Failed to get shared local drive data, command error")
            return False, "Failed to get output of command 'net share' "
        else:
            cmd_out = cmd_out.split("\n")
        i = 4
        position_resource = cmd_out[1].find("Resource")
        position_remark = cmd_out[1].find("Remark")
        shared_drives = {}
        while i < len(cmd_out) - 3:
            share_name = cmd_out[i][0:position_resource].strip()
            if not share_name.endswith("$"):
                resource = cmd_out[i][position_resource:position_remark].strip()
                pc_name = os.environ['COMPUTERNAME']
                if no_hostname:
                    pc_name = "!@WINSHAREIP@!"
                shared_drives[resource] = ["\\\\{}\\{}".format(pc_name, share_name), share_name]
            i = i + 1
        return True, shared_drives

    @staticmethod
    def __add_new_share(drive_letter, share_name=None):
        # Check if share name is already used, if not create a share else return false
        share_name = share_name.replace(" ", "")
        drive_letter = drive_letter[0].upper()
        logger.debug("Attempting to create a new share for: %s, using name: %s", drive_letter, share_name)
        if share_name is None:
            share_name = drive_letter
        # The drive is ready to be shared
        cmd_out = uac_cmd_exec("net share {sharename}={location} /grant:everyone,FULL".format(
            sharename=share_name,
            location=drive_letter + ":\\"))
        if cmd_out is None:
            logger.error("Failed to create new share, Maybe the UAC prompt was dismissed !")
            return False, "Failed to create new share, Maybe the UAC prompt was dismissed !"
        elif "The name has already been shared" in cmd_out:
            logger.error("The share name %s is already in use, try another one")
            return False, "The share name is already used"
        elif "was shared successfully" in cmd_out:
            logger.debug("Share created for drive letter '%s' at '%s"'', drive_letter,
                         "\\\\{}\\{}".format(os.environ['COMPUTERNAME'], share_name))
            return True, {drive_letter + ":\\": "\\\\{}\\{}".format(os.environ['COMPUTERNAME'], share_name)}
        else:
            logger.error("Unknown error while creating share. `%s`", cmd_out)
            return False, "Something went wrong when creating share. '{}'".format(cmd_out)

    @staticmethod
    def __remove_share(name):
        # Check if share exists and if it exists remove it
        logger.debug("Attempting to delete a share: %s", name)
        cmd_out = uac_cmd_exec("net share {name} /delete".format(name=name))
        if cmd_out is None:
            logger.error("Failed to delete the share, Maybe the UAC prompt was dismissed !")
            return False, "Failed to delete the share, Maybe the UAC prompt was dismissed !"
        elif "matching share could not be found so nothing was deleted" in cmd_out:
            logger.warning("The share name '%s' to delete does not exist!", name)
            return False, "The share name to delete does not exist"
        elif "was deleted successfully" in cmd_out:
            logger.debug("Shared '%s' was removed", name)
            return True, "Share '{}' was deleted !".format(name)
        else:
            logger.error("Unknown error while removing share. `%s`", cmd_out)
            return False, "Something went wrong when removing the share. '{}'".format(cmd_out.strip())

    def path_on_host(self, local_path):
        full_path = local_path

        logger.debug("Attempting path translation for '%s'", full_path)
        # If this a a existing path, return translated path, else just return None and input path untouched
        # Linux like path like "/home/" will not exist here and will be returned back as it is
        if os.path.exists(full_path):
            full_path = os.path.abspath(local_path)
            # This regular expression to test UNC paths, found on internet
            np_reg = r'^(\\\\[\w\.\-_]+\\[^\\/:<>|""]+)((?:\\[^\\/:<>|""]+)*\\?)$'
            cfgvars.refresh_config()

            # This file is from linux host
            if full_path.startswith("Z:\\") or full_path.startswith("\\\\tsclient\\root\\"):
                # Just remove prefix and replace slashes and we are good to go
                return True, full_path.replace("Z:", "").replace("\\\\tsclient\\root", "").replace("\\", "/")

            # The initials of full_path 'C:\\' is in keys of remembered_maps, It is a path on linux mapped to drive
            elif full_path[:3] in cfgvars.config["remembered_maps"]:
                # Just replace "drive_letter":\\ with the path on host and "\" to "/"
                host_path = full_path.replace(full_path[:2],
                                              cfgvars.config["remembered_maps"][full_path[:3]][1]
                                              ).replace("\\", "/")
                return True, host_path

            # Check if it looks like a network path, if it is checked,  it is network location of shared location on
            # linux
            elif re.match(np_reg, full_path):
                for remembered_map in cfgvars.config["remembered_maps"]:
                    if full_path.startswith(cfgvars.config["remembered_maps"][remembered_map][0]):
                        host_path = full_path.replace(
                            cfgvars.config["remembered_maps"][remembered_map][0],
                            cfgvars.config["remembered_maps"][remembered_map][1]
                        ).replace("\\", "/")
                        return True, host_path
                logger.warning("This path (network location) should be mapped and shared for path translation", full_path)
                return False, "This network location should be mapped and shared before it can be accessed from host"

            # Now it must be any other local drive on windows, check if it is shared, if not return error
            else:
                status, shares = self.__get_shared_drives()
                if full_path[:3] in shares:
                    # as: C:\dir\somefile.pdf -> \\PC-HOSTNAME\sharename\dir\somefile.pdf ->
                    # !@WINSHAREIP@!/cdrive/dir/somefile.pdf
                    net_path = shares[full_path[:3]][0]

                    host_path = full_path.replace(full_path[:2], net_path).replace(
                        "\\\\{}\\".format(os.environ['COMPUTERNAME']),
                        "\\\\!@WINSHAREIP@!\\"
                    ).replace("\\", "/")
                    return True, host_path
                else:
                    # The drive is not shared, return false
                    logger.error("This path cannot be translated to path on host because it is not shared (%s)", full_path)
                    return False, "This file's path cannot be translated to path on host because drive containing it " \
                                  "is not shared "
        else:
            # This is not a path that exists on Windows, maybe any other string, maybe linux path (Don't deal with
            # it here)
            logger.warning("The path '%s' is not a valid windows path or path does not exist", full_path)
            return None, local_path

    def run_cmd(self, cmd):
        # Passed cmd is a list containing command followed by parameters, This function get called
        # When a command is received normally
        if cmd[0] == "add-drive-share":
            try:
                status, message = self.__add_new_share(cmd[1], cmd[2])
                return status, message
            except IndexError:
                return False, "Command 'add-drive-share' is missing parameter. Required: drive_letter, share_name "
        elif cmd[0] == "get-drive-shares":
            status, message = self.__get_shared_drives(no_hostname=True)
            return status, message
        elif cmd[0] == "rem-drive-share":
            try:
                status, message = self.__remove_share(cmd[1])
                return status, message
            except IndexError:
                return False, "Command 'rem-drive-share' is missing parameter. Required: share_name/drive_letter "
        elif cmd[0] == "add-network-map":
            try:
                status, message = self.__add_new_map(cmd[1], cmd[2], cmd[3])
                return status, message
            except IndexError:
                return False, "Command 'add-network-map' missing parameter. Required: host_path, network_location, " \
                              "drive_letter "
        elif cmd[0] == "get-network-map":
            cfgvars.refresh_config()
            return True, cfgvars.config["remembered_maps"]
        elif cmd[0] == "rem-network-map":
            try:
                status, message = self.__remove_map(cmd[1])
                return status, message
            except IndexError:
                return False, "Command 'rem-network-map' is missing parameter. Required: network_location/drive_letter"
        else:
            return False, None
