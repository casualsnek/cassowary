import traceback

from ..helper import uac_cmd_exec
from ..cfgvars import cfgvars
from base.log import get_logger


logger = get_logger(__name__)


class FileAssociation:
    def __init__(self):
        #
        #    config.json -> [remembered_assocs]
        #                        <file_extension> : <older_ftype>
        #                        "zip" : "CompressedFolder"

        self.CMDS = ["get-associations", "set-association", "unset-association"]
        self.NAME = "assocommands"
        self.DESC = "File Associations Helper - Creates 'casualhXDGO' ftype which xdg-opens a file on host system"
        # This should create a ftype which is associated to xdg_open_handle bin
        # Setting new associations should record previous ftype of extension for easy removal of association
        # Check if ftype is set to xdg_open_handle_bin %1 if not set it
        cmd_out = uac_cmd_exec("ftype {}".format(cfgvars.config["assoc_ftype"]), noadmin=True)
        if cfgvars.config["xdg_open_handle"] not in cmd_out:
            logger.error("Ftype not associated to app, dobule clicking file will not trigger xdg-open")
            logger.debug("Trying to fix ftype and open command string")
            # ftype not set
            if "no open command associated with it" in cmd_out:
                uac_cmd_exec("assoc .xdgo={ftype}".format(ftype=cfgvars.config["assoc_ftype"]))
            uac_cmd_exec('ftype {ftype}={launch_str}'.format(
                ftype=cfgvars.config["assoc_ftype"],
                launch_str=cfgvars.config["xdg_open_handle"])
            )

    @staticmethod
    def __get_associations():
        logger.debug("Fetching file extensions associated to our ftype")
        associated_exts = []
        cmd_out = uac_cmd_exec("assoc", noadmin=True, non_blocking=False)
        if cmd_out is None:
            return False, "Cannot get association info"
        else:
            cmd_out = cmd_out.split("\n")
            for line in cmd_out:
                line = line.strip()
                if line.endswith(cfgvars.config["assoc_ftype"]):
                    associated_exts.append(line.split("=")[0][1:])
            return True, associated_exts

    @staticmethod
    def __set_association(file_format):
        file_format = file_format.strip()
        logger.debug("Setting association to file format '.%s'", file_format)
        # Get current associated ftype: assoc .format  ->  .format=ftype
        cmd_out = uac_cmd_exec("assoc .{extension}".format(extension=file_format), noadmin=True)
        old_association = ""
        if file_format in ["exe", "msi"]:
            return False, "Refusing to change association for this file type as this might break the system ! "
        if cmd_out is not None:
            if " association not found for extension" not in cmd_out:
                # An ftype is associated with this extension
                old_association = cmd_out.strip().split("=")[1]
            cmd_out = uac_cmd_exec("assoc .{extension}={ftype}".format(extension=file_format,
                                                                       ftype=cfgvars.config["assoc_ftype"]
                                                                       ))
            if cmd_out is not None:
                if cfgvars.config["assoc_ftype"] in cmd_out:
                    # Do not remove old ftype if it already exists, else add new entry
                    cfgvars.refresh_config()
                    if file_format not in cfgvars.config["remembered_assocs"]:
                        # Backup for this file extension does not exist, create one
                        cfgvars.config["remembered_assocs"][file_format] = old_association
                        cfgvars.save_config()
                    return True, "Successfully associated to file extension '.{}'".format(file_format)
                else:
                    logger.error("Unexpected error while setting association. '%s' ", cmd_out)
                    return False, "Unexpected error while setting association. '{}' ".format(cmd_out)
            else:
                logger.error("Failed to set association for '.%s', Maybe the UAC prompt was dismissed !", file_format)
                return False, "Failed to set new association, Maybe the UAC prompt was dismissed !"
        else:
            logger.error("Command failed for getting current associations")
            return False, "Error getting current association for '{}' extension. (Command failed) ".format(file_format)

    @staticmethod
    def __unset_associations(file_format):
        file_format = file_format.strip()
        logger.debug("Removing association to file format '.%s'", file_format)
        cmd_out = uac_cmd_exec("assoc .{extension}".format(extension=file_format), noadmin=True)
        if cmd_out is not None:
            current_ftype = cmd_out.strip().split("=")[1]
            cfgvars.refresh_config()
            if current_ftype == cfgvars.config["assoc_ftype"]:
                # This file extension is associated to this tool, rollback to older ftype from backup
                # If backup does not exist for this file extension, remove the association (Unknown file format)
                old_ftype = ""
                if file_format in cfgvars.config["remembered_assocs"]:
                    old_ftype = cfgvars.config["remembered_assocs"][file_format]
                cmd_out = uac_cmd_exec("assoc .{extension}={ftype}".format(extension=file_format, ftype=old_ftype))
                if cmd_out is not None:
                    if old_ftype in cmd_out:
                        # Un setting was successful
                        if file_format in cfgvars.config["remembered_assocs"]:
                            cfgvars.config["remembered_assocs"].pop(file_format)
                            cfgvars.save_config()
                        return True, "Removed association with file format '.{}'".format(file_format)
                    else:
                        logger.error("Unexpected error while removing association. '%s' ", cmd_out)
                        return False, "Unexpected error while un setting association. '{}' ".format(cmd_out)
                else:
                    logger.error("Failed to remove association, Maybe the UAC prompt was dismissed !")
                    return False, "Failed to unset association, Maybe the UAC prompt was dismissed !"
            elif file_format in cfgvars.config["remembered_assocs"]:
                # Association was previously set but was changed manually, just remove from backup, return false
                cfgvars.config["remembered_assocs"].pop(file_format)
                cfgvars.save_config()
                logger.warning("No longer associated to this format '.%s', maybe external change was done", file_format)
                return False, "No longer associated to this file format '{}', (Backup cleared)".format(file_format)
            else:
                logger.warning("Not associated to this file format '.%s'", file_format)
                return False, "Not associated to this file format '{}'".format(file_format)
        else:
            logger.error("Command failed for getting current associations")
            return False, "Error getting current association for '{}' extension. (Command failed) ".format(file_format)

    def run_cmd(self, cmd):
        if cmd[0] == "get-associations":
            status, message = self.__get_associations()
            return status, message
        elif cmd[0] == "set-association":
            try:
                status, message = self.__set_association(cmd[1])
                return status, message
            except IndexError:
                logger.warning("Error setting file association, Command - %s  : %s", str(cmd), traceback.format_exc())
                return False, "Command 'set-association' is missing parameter. Required: file_extension "
        elif cmd[0] == "unset-association":
            try:
                status, message = self.__unset_associations(cmd[1])
                return status, message
            except IndexError:
                logger.warning("Error Unsetting file association, Command - %s  : %s", str(cmd), traceback.format_exc())
                return False, "Command 'unset-association' is missing parameter. Required: file_extension "
        else:
            return False, None
