import random
import string
import time
import subprocess
import traceback

from .cfgvars import cfgvars
from .log import get_logger
import os
import re
import libvirt

logger = get_logger(__name__)


def randomstr(leng=4):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(leng))


def warn_dependencies():
    required_bins = ["xfreerdp", "update-desktop-database", "mount", "virsh", "pkexec"]
    for depend in required_bins:
        path = os.popen("which " + depend).read().strip()
        if path == "":
            logger.warning("Missing dependency '%s', may cause issues during runtime")


def ip_by_vm_name(name):
    conn = libvirt.open(cfgvars.config["libvirt_uri"])
    if conn is not None:
        try:
            dom = conn.lookupByName(name)
            interfaces = dom.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)
            if interfaces is not None:
                for interface in interfaces:
                    try:
                        ip = interfaces[interface]["addrs"][0]["addr"]
                        return ip
                    except (KeyError, IndexError) as e:
                        pass
            else:
                logger.error("Cannot get network interfaces for domain '%s' ", name)
        except libvirt.libvirtError:
            logger.error("Cannot get ip for '%s' -> %s", name, traceback.format_exc())
    else:
        logger.error("Cannot connect to libvirt ! at '%s' ", cfgvars.config["libvirt_uri"])
    logger.warning("Could not get proper ip address for domain '%s' ", name)
    return None


def replace_vars(inp_string):
    values = {
        "!@WINSHAREIP@!": cfgvars.config["host"],
        "!@WINSHAREPORT@!": cfgvars.config["port"],
        "!@WINHOSTNAME@!": cfgvars.config["winvm_hostname"],
        "!@WINUSERNAME@!": cfgvars.config["winvm_username"],
        "!@WINSHAREMOUNTROOT@!": cfgvars.config["winshare_mount_root"],
    }
    for value in values:
        if value in inp_string:
            inp_string = inp_string.replace(value, values[value])
    return inp_string


def create_request(command, message_id=None):
    if type(command) is not list:
        if type(command) is dict:
            command = list(command)
        command = str(command).split(" ")
    if message_id is None:
        message_id = randomstr()
    return {
        "id": message_id,
        "type": "request",
        "command": command
    }


def get_windows_cifs_locations():
    cmd_out = os.popen("mount -t cifs").read().strip().split("\n")
    output = {}
    if cmd_out == [""]:
        return output
    for line in cmd_out:
        net_loc = line[0:line.find(" on /")].strip()
        output[line[len(net_loc + " on "):line.find(" type cifs (")].strip()] = net_loc.replace("/", "\\")
    return output


def mount_pending():
    mount = ""
    uid = os.popen("id -u").read().strip()
    gid = os.popen("id -g").read().strip()
    swapped_mounted_locations = dict((value, key) for key, value in get_windows_cifs_locations().items())
    expanded_cached_shares = var_expanded_shares()
    for resource_path in expanded_cached_shares:
        if expanded_cached_shares[resource_path][0] not in swapped_mounted_locations:
            # This network share is not mounted, create a command to create directory to mount it and command to
            # actually mount it
            mount_point = os.path.join(cfgvars.config["winshare_mount_root"], expanded_cached_shares[resource_path][1])
            mount = mount + 'mkdir -p {mount_pt} && mount -t cifs -o username="{win_uname}",' \
                            'password="{win_pass}",uid={uid},gid={gid} "{net_loc}" "{mount_pt}" && '.format(
                win_uname=cfgvars.config["winvm_username"], win_pass=cfgvars.config["winvm_password"],
                mount_pt=mount_point, net_loc=expanded_cached_shares[resource_path][0], uid=uid, gid=gid
            )
    mount = mount[:-4]
    if mount != "":
        logger.debug("Generated mount command: '%s'", mount)
        if os.environ.get("DIALOG_MODE") == "console":
            logger.debug("Dialog mode set to console.. Using xterm to mount remote drives")
            os.popen("xterm -T 'casualRDH | Enter sudo password to mount drives' -e sudo sh -c '{command}'".format(
                command=mount
            ).replace("\\", "/")).read()
        else:
            os.popen("pkexec sh -c '{command}'".format(command=mount).replace("\\", "/")).read()


def unmount_all():
    swapped_mounted_locations = dict((value, key) for key, value in get_windows_cifs_locations().items())
    expanded_cached_shares = var_expanded_shares()
    umount_cmd = ""
    for resource_path in expanded_cached_shares:
        if expanded_cached_shares[resource_path][0] in swapped_mounted_locations:
            mount_pt = swapped_mounted_locations[expanded_cached_shares[resource_path][0]]
            umount_cmd = umount_cmd + "umount '{mount_pt}' && ".format(mount_pt=mount_pt)
    umount_cmd = umount_cmd[:-4]
    if umount_cmd != "":
        logger.debug("Genetared unmount command: '%s'", umount_cmd)
        if os.environ.get("DIALOG_MODE") == "console":
            logger.debug("Dialog mode set to console.. Using xterm to unmount remote drives")
            os.popen("xterm -T 'casualRDH | Enter sudo password to unmount drives' -e sudo sh -c '{command}'".format(
                command=umount_cmd
            ).replace("\\", "/")).read()
        else:
            os.popen("pkexec sh -c '{command}'".format(command=umount_cmd))


def var_expanded_shares():
    x = cfgvars.config["cached_drive_shares"]
    for resource in x:
        x[resource][0] = replace_vars(x[resource][0])
    return x


def handle_win_ip_paths(path, attempts=2):
    if "!@WINSHAREIP@!" in path:
        attempt = 1
        path_found = False
        while attempt <= attempts:
            expanded_path = replace_vars(path)
            mounted = dict((value, key) for key, value in get_windows_cifs_locations().items())
            print(mounted, get_windows_cifs_locations())
            # First check if it is mounted
            for net_loc in mounted:
                print(net_loc.replace("\\", "/"), expanded_path)
                # (//192.x.x.x/c)/user/somefile.txt
                #     ^----(/mnt/casualrdh/c)/user/somefile.txt
                if expanded_path.startswith(net_loc.replace("\\", "/")):
                    print(expanded_path.startswith(net_loc.replace("\\", "/")))
                    # The location is mounted,
                    path = expanded_path.replace(net_loc.replace("\\", "/"), mounted[net_loc])
                    path_found = True
                    break
            # If it is not try mounting, since we cannot know if polkit has completed
            # wait 10 seconds and check if it it mounted again
            # If mounted ok, else return failure
            if not path_found:
                mount_pending()
                attempt = attempt + 1
            else:
                break
        # It is not a path or a valid path
        if path_found:
            return True, path
        else:
            return False, path
    else:
        return None, path


# Return {"/mnt/casual/d": "\\192.168.40.11\d"}
# {"C:\": ["\\192.168.40.11\c", "c"]}


def path_translate_to_guest(path):
    # If the path exists translate the path, else return the input untouched
    full_path = os.path.abspath(path)
    if os.path.exists(full_path):
        cached_shares = var_expanded_shares()
        mounts = get_windows_cifs_locations()
        # Check if the file being accessed is a mounted windows share
        for mount in mounts:
            if full_path.startswith(mount):
                # This is a mounted windows location, return windows native location, instead of path mapped back to Z:|
                for resource in cached_shares:
                    if cached_shares[resource][0] == mounts[mount]:  # mounts[mount] is net location of mount point
                        if resource.endswith("\\") and full_path != mount:
                            resource = resource[:-1]
                        # resource is windows location of net share
                        return full_path.replace(mount, resource).replace("/", "\\")
        # It is not a windows location, I expect root '/' to be always mounted as Z:\ so ....
        return ("Z:" + full_path).replace("/", "\\")
    else:
        return path


def create_reply(message, data, status):
    message["type"] = "response"
    message["status"] = 1 if status else 0
    message["data"] = data
    return message

def full_rdp():
    command = '{rdc} /d:"{domain}" /u:"{user}" /p:"{passd}" /v:{ip} /a:drive,root,/ +auto-reconnect +clipboard '\
              '/cert-ignore /audio-mode:1 /scale:{scale} /wm-class:"cassowaryApp-FULLSESSION" /dynamic-resolution' \
              ' /{mflag} {rdflag} 1> /dev/null 2>&1 &'
    multimon_enable = int(os.environ.get("RDP_MULTIMON", cfgvars.config["rdp_multimon"]))
    cmd_final = command.format(
        rdflag=cfgvars.config["rdp_flags"],
        domain=cfgvars.config["winvm_hostname"],
        user=cfgvars.config["winvm_username"],
        passd=cfgvars.config["winvm_password"],
        ip=cfgvars.config["host"],
        scale=cfgvars.config["rdp_scale"],
        rdc = cfgvars.config["full_session_client"],
        mflag="multimon" if multimon_enable else "span"
    )
    logger.debug("Creating a full RDP session with commandline  : " + command)
    process = subprocess.Popen(["sh", "-c", "{}".format(cmd_final)])
    process.wait()
    logger.debug("Full RDP session ended !")

def vm_suspension_handler():
    logger.debug("VM watcher active !")
    logger.debug("VM suspend on inactivity is "+"enabled" if bool(cfgvars.config["vm_auto_suspend"]) else "disabled")
    last_active_on = int(time.time()) # Should at least wait for one timeout
    tc = 0
    vm_app_launch_marker = "/tmp/cassowary-app-launched.state"
    vm_suspend_file = "/tmp/cassowary-vm-state-suspend.state"
    while True:
        if bool(cfgvars.config["vm_auto_suspend"]) and cfgvars.config["vm_name"].strip() != "":
            process = subprocess.check_output(["ps", "auxfww"])
            # Check if any cassowary started freerdp process is running or not
            # print("Seconds of inactivity:", int(time.time()) - last_active_on, "Will sleep after :", cfgvars.config["vm_suspend_delay"])
            if len(re.findall(r"freerdp.*\/wm-class:.*cassowaryApp", process.decode())) >= 1 or len(re.findall(r".*cassowary -a", process.decode())) >= 1:
                last_active_on = int(time.time())  # Process exists, set last active to current time and do nothing else
                print("Process exists ! Doing nothing...")
            elif int(time.time()) - last_active_on > cfgvars.config["vm_suspend_delay"] \
                        and not os.path.isfile(vm_suspend_file):
                bypass = False
                # No cassowary process is running. The VM was relaunched (cassowary should remove this file if any app
                # are run through it), and inactivity time is >= required, so put it to sleep
                if os.path.isfile(vm_app_launch_marker):
                    logger.debug("Found a app launch marker file")
                    with open(vm_app_launch_marker, "r") as mf:
                        last_proc_spawned_on = int(mf.read().strip())
                    # If last process was created within last 10 seconds, do not suspend
                    if int(time.time()) - last_proc_spawned_on < 10:
                        bypass = True
                        logger.debug("This vm suspend was cancelled as user attempted to launch app right now !")
                    else:
                        os.remove(vm_app_launch_marker) # Delete marker file older than 10 sec
                logger.debug("Suspending VM due to inactivity !")
                conn = libvirt.open(cfgvars.config["libvirt_uri"])
                if conn is not None and bypass is False:
                    try:
                        dom = conn.lookupByName(cfgvars.config["vm_name"])
                        dom.suspend()
                        logger.debug("VM '%s' suspended due to inactivity: ", cfgvars.config["vm_name"])
                        logger.debug("Creating suspension marker file")
                        open(vm_suspend_file, "w").write("vm-suspended-at-" + str(time.time()))
                    except libvirt.libvirtError:
                        logger.error("Could not suspend vm '%s' -> %s", cfgvars.config["vm_name"],
                                     traceback.format_exc())
                else:
                    if conn is not None:
                        logger.error("Cannot connect to libvirt ! at '%s'", cfgvars.config["libvirt_uri"])
                # We also Checked if the vm suspend file exists, if it exists that means we previously suspended VM due to
                # inactivity and vm was not resumed by cassowary ! As user may be using VM directly through virt-manager
                # , which we don't want to suspend that session, next suspension happens after next cassowary usage
            # Else, either the VM was suspended and no cassowary application has been launched since then, or we do not
            # have required inactivity duration, do nothing just wait
        time.sleep(2)
        if tc >= 10:
            tc = 0
            logger.debug("Refreshing config to update to probable config changes !")
            cfgvars.refresh_config()

def fix_black_window(forced=False):
    first_launch_track = "/tmp/cassowary-rdp-login-done.state"
    if not os.path.isfile(first_launch_track) or forced:
        # The test window was forced or no other window was opened prevouusly
        logger.debug("Opening & closing a test window to trigger login or try to fix black screen bug on first launch")
        cmd = 'xfreerdp /d:"{domain}" /u:"{user}" /p:"{passd}" /v:"{ip}" +clipboard /a:drive,root,/ ' \
              '+decorations /cert-ignore /audio-mode:1 /scale:100 /dynamic-resolution /span  ' \
              '/wm-class:"cassowaryApp-echo" /app:"cmd.exe"'.format(domain=cfgvars.config["winvm_hostname"],
                                                                    user=cfgvars.config["winvm_username"],
                                                                    passd=cfgvars.config["winvm_password"],
                                                                    ip=cfgvars.config["host"]
                                                                    )
        process = subprocess.Popen(["sh", "-c", "{}".format(cmd)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ts = int(time.time())
        while process.poll() is None:
            for line in process.stdout:
                if "xf_lock_x11" in line or int(time.time()) - ts > 10:
                    open(first_launch_track, "w").write(str(int(time.time())))
                    logger.debug("Created a marker -> One session done")
                    # Create file to remember that one session was already done
                    process.kill()
    logger.debug("An app was already opened, the black window should not appear now !")

def vm_wake():
    vm_suspend_file = "/tmp/cassowary-vm-state-suspend.state"
    vm_app_launch_marker = "/tmp/cassowary-app-launched.state"
    logger.debug("Attempting to resume VM")
    # If VM name is not set it may be windows instanced elsewhere which we cannot pause or resume !
    # Since this function will be called everytime an cassowary application is launched,
    # Add a file with timestamp for notifying vm_suspension_handler from background client that an app was launched just
    # now so delay suspend by few seconds while the application process is created !
    with open(vm_app_launch_marker, "w") as mf:
        mf.write(str(int(time.time())))
    if cfgvars.config["vm_name"].strip() != "":
        conn = libvirt.open(cfgvars.config["libvirt_uri"])
        if conn is not None:
            try:
                dom = conn.lookupByName(cfgvars.config["vm_name"])
                if dom.info()[0] == 3:
                    logger.debug("VM was suspended.. Resuming it")
                    dom.resume()
                    logger.debug("VM resumed..")
                    if os.path.isfile(vm_suspend_file):
                        logger.debug(
                            "Found suspend state file... VM was auto suspended previously, clearing it for next session")
                        os.remove(vm_suspend_file)
                    logger.debug("Added 2 sec delay for VM networking to be active !")
                    time.sleep(2)
                else:
                    logger.warning("VM state is not set to suspended : State -> '%s' ", str(dom.info()[0]))
            except libvirt.libvirtError:
                logger.error("Could not suspend vm '%s' -> %s", cfgvars.config["vm_name"],
                             traceback.format_exc())
        else:
            logger.error("Cannot connect to libvirt ! at '%s'", cfgvars.config["libvirt_uri"])
    else:
        logger.debug("VM name is blank, maybe not a vm skipping vm resume process !")

# Note: VM suspend file is for preventing suspending vm sessions manually started by user without using cassowary
#        App launcher marker file is prevent vm from suspending right before an app is launched !