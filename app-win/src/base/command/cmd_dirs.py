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
                logger.debug("Z: is not mapped... Mapping now")
                # No map for root, create one now
                uac_cmd_exec("net use Z: /delete", noadmin=True, timeout=8)
                cmd_out = uac_cmd_exec("net use Z: \"\\\\tsclient\\root\" /persistent:Yes", noadmin=True, timeout=8)
                if "command completed successfully" in cmd_out:
                    logger.debug("Host root is now mounted as Z :) ")
                else:
                    logger.error("Failed to map host root to Z: -> net use command returned: "+cmd_out)
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
        nl = [y for y in cmd_out[3].split("  ") if y != ""]
        position_local = cmd_out[3].find(nl[1])
        position_remote = cmd_out[3].find(nl[2])
        position_network = cmd_out[3].find(nl[3])
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
            # Drive letter is not used, good to go,
            command_line = "net use {drive_letter}: \"{network_location}\" /persistent:Yes".format(
                drive_letter=drive_letter,
                network_location=network_location.strip()
            )
            cmd_out = uac_cmd_exec(command_line, noadmin=True)
            active_maps = self.__get_active_network_maps()
            if drive_letter + ":\\" in active_maps:
                cfgvars.refresh_config()
                # Keep a record of remote host path for this map
                cfgvars.config["remembered_maps"][drive_letter + ":\\"] = [network_location, remote_path]
                cfgvars.save_config()
                logger.debug("Added mapping from '%s' to letter '%s' resolving to host path '%s'", network_location,
                             drive_letter, remote_path)
                return True, "Host path '{}' is now mapped to drive '{}' ".format(remote_path, drive_letter)
            else:
                logger.error("Unknown error while trying to map to drive '%s' => Used commandline: %s", cmd_out,
                             command_line)
                return False, "Error while trying to map to drive: \n'{}'".format(cmd_out.split("\n")[-1])
        else:
            logger.warning("Map not added, drive letter already in use")
            return False, "The drive letter is already in use"

    def __remove_map(self, name):
        logger.debug("Attempting to remove network mapping of : %s", name)
        if not name.startswith("\\\\"):
            name = name[0].upper() + ":"
        cmd_out = uac_cmd_exec("net use {name} /delete".format(name=name), noadmin=True)
        active_maps = self.__get_active_network_maps()
        if name+"\\" not in active_maps:
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
        else:
            logger.warning("Not removed network location Map to '%s' does not exist or error : %s -> MAPS: %s",
                           name, cmd_out, str(active_maps))
            return False, "Error removing mapping for '{}'. \n".format(name, cmd_out.split("\n")[-1])

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
        nl = [y for y in cmd_out[1].split("  ") if y != ""]
        position_resource = cmd_out[1].find(nl[1])
        position_remark = cmd_out[1].find(nl[2])
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

    def __add_new_share(self, drive_letter, share_name=None):
        # Check if share name is already used, if not create a share else return false
        share_name = share_name.replace(" ", "")
        drive_letter = drive_letter[0].upper()
        logger.debug("Attempting to create a new share for: %s, using name: %s", drive_letter, share_name)
        status, active_shares = self.__get_shared_drives()
        if share_name is None:
            share_name = drive_letter
        # The drive is ready to be shared
        if drive_letter+":\\" in active_shares:
            logger.warning("Drive %s semms to shared already ! Shared drives: %s ", drive_letter, str(active_shares))
            return "Drive %s:\\ is already shared !"
        cmd_out = uac_cmd_exec("net share {sharename}={location} /grant:everyone,FULL".format(
                                sharename=share_name, location=drive_letter + ":\\"))
        status, active_shares = self.__get_shared_drives()
        if cmd_out is None or cmd_out == "":
            logger.error("Failed to create new share, Maybe the UAC prompt was dismissed !")
            return False, "Failed to create new share, Maybe the UAC prompt was dismissed !"
        elif drive_letter+":\\" in active_shares or cmd_out.split(" ")[0] == share_name:
            logger.debug("Share created for drive letter '%s' at '%s"'', drive_letter,
                         "\\\\{}\\{}".format(os.environ['COMPUTERNAME'], share_name))
            return True, {drive_letter + ":\\": "\\\\{}\\{}".format(os.environ['COMPUTERNAME'], share_name)}
        else:
            logger.error("Error while creating share. `%s` -> Active shares: %s", cmd_out, str(active_shares))
            return False, "Error while creating share. \n'{}'".format(cmd_out)

    def __remove_share(self, name):
        # Check if share exists and if it exists remove it
        logger.debug("Attempting to delete a share: %s", name)
        cmd_out = uac_cmd_exec("net share {name} /delete".format(name=name))
        status, active_shares = self.__get_shared_drives()
        shared_switched = {}
        print("Active shares: "+str(active_shares))
        if status is None:
            logger.error("Failed to fetch currently shared drives")
            return False, active_shares
        for drive_letter in active_shares:
            shared_switched[active_shares[drive_letter][1]] = [active_shares[drive_letter][0], drive_letter]
        if cmd_out is None:
            logger.error("Failed to delete the share, Maybe the UAC prompt was dismissed !")
            return False, "Failed to delete the share, Maybe the UAC prompt was dismissed !"
        elif name not in shared_switched:
            logger.debug("Shared '%s' was removed", name)
            return True, "Share '{}' was deleted !".format(name)
        else:
            logger.error("Error while removing share.. `%s`", cmd_out)
            return False, "Error while removing share. \n'{}'".format(cmd_out.strip())

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
                logger.warning("Failed creating drive share. Params: %s", str(cmd))
                return False, "Command 'add-drive-share' is missing parameter. Required: drive_letter, share_name "
        elif cmd[0] == "get-drive-shares":
            status, message = self.__get_shared_drives(no_hostname=True)
            return status, message
        elif cmd[0] == "rem-drive-share":
            try:
                status, message = self.__remove_share(cmd[1])
                return status, message
            except IndexError:
                logger.warning("Failed removing drive share. Params: %s", str(cmd))
                return False, "Command 'rem-drive-share' is missing parameter. Required: share_name/drive_letter "
        elif cmd[0] == "add-network-map":
            try:
                status, message = self.__add_new_map(cmd[1], cmd[2], cmd[3])
                return status, message
            except IndexError:
                logger.warning("Failed adding network map. Params: %s", str(cmd))
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
                logger.warning("Failed removing network map. Params: %s", str(cmd))
                return False, "Command 'rem-network-map' is missing parameter. Required: network_location/drive_letter"
        else:
            return False, None
