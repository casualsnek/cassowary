import os
from base.cfgvars import cfgvars


def get_basic_info(client, timeout=5):
    if client is None:
        return False, "Unable to fetch network mapping information ! \n Not connected to server"
    response = client.send_wait_response(["get-basic-info"], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not fetch basic info the server due to timeout.\nMake sure server is reachable !"


def get_network_maps(client, timeout=5):
    if client is None:
        return False, "Unable to fetch network mapping information ! \n Not connected to server"
    response = client.send_wait_response(["get-network-map"], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not fetch drive maps from the server due to timeout.\nMake sure server is reachable !"


def add_network_map(client, local_path, share_name, drive_letter, timeout=20):
    if not os.path.exists(local_path):
        return False, "The local path '{}' does not exist".format(local_path)
    if not os.path.isdir(local_path):
        return False, "The local path '{}' is a file, directory path is required !".format(local_path)
    if client is None:
        return False, "Unable to send new map info ! \n Not connected to server"
    response = client.send_wait_response(["add-network-map", local_path, share_name, drive_letter], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not new send drive maps to the server due to timeout.\nMake sure server is reachable !"


def rem_network_map(client, name, timeout=20):
    if client is None:
        return False, "Unable to fetch network mapping information ! \n Not connected to server"
    response = client.send_wait_response(["rem-network-map", name], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not remove drive maps from the server due to timeout.\n Make sure server is reachable !"


def get_network_shares(client, timeout=5):
    if client is None:
        return False, "Unable to fetch shared drives information ! \n Not connected to server"
    response = client.send_wait_response(["get-drive-shares"], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            cfgvars.config["cached_drive_shares"] = response["data"]
            cfgvars.save_config()
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not fetch shared drive information from the server (Timeout).\n Make sure server is reachable!"


def add_network_share(client, drive_letter, share_name=None, timeout=20):
    drive_letter = drive_letter[0].upper()
    if share_name is None:
        share_name = drive_letter.lower()
    if client is None:
        return False, "Unable to send request to share a new drive ! \n Not connected to server"
    response = client.send_wait_response(["add-drive-share", drive_letter, share_name], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not add new share in the server (Timeout).\n Make sure server is reachable !"


def rem_network_share(client, share_name, timeout=20):
    if client is None:
        return False, "Unable to fetch network mapping information ! \n Not connected to server"
    response = client.send_wait_response(["rem-drive-share", share_name], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not remove drive maps from the server due to timeout.\n Make sure server is reachable !"


def get_installed_apps(client, timeout=20):
    if client is None:
        return False, "Unable to fetch installed application information ! \n Not connected to server"
    response = client.send_wait_response(["get-installed-apps"], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not get installed app list from the server due to timeout.\n " \
                  "Make sure server is reachable or increase timeout value!"


def get_association(client, timeout=20):
    if client is None:
        return False, "Unable to fetch file association list ! \n Not connected to server"
    response = client.send_wait_response(["get-associations"], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not get file association information from the server due to timeout.\n " \
                  "Make sure server is reachable or increase timeout value!"


def set_association(client, file_extension, timeout=20):
    if client is None:
        return False, "Unable to fetch file association information ! \n Not connected to server"
    response = client.send_wait_response(["set-association", file_extension], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not set file association due to timeout.\n " \
                  "Make sure server is reachable or increase timeout value!"


def unset_association(client, file_extension, timeout=20):
    if client is None:
        return False, "Unable to fetch file association information ! \n Not connected to server"
    response = client.send_wait_response(["unset-association", file_extension], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return False, "Request failed !\n {}".format(response["data"])
    return False, "Could not remove file association due to timeout.\n " \
                  "Make sure server is reachable or increase timeout value!"


def get_exe_icon(client, file_path, timeout=20):
    # TODO: Actually get app icon, Return default icon if request fails !s
    if client is None:
        return False, "Unable to fetch file association information ! \n Not connected to server"
    response = client.send_wait_response(["get-exe-icon", file_path], timeout=timeout)
    if response is not False:
        if bool(response["status"]):
            return True, response["data"]
        return True, ''
    return False, "Could not get icon for '{}' .\n " \
                  "Make sure server is reachable or increase timeout value!".format(file_path)
