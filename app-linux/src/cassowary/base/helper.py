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
from cassowary.gui.components.vmstart import StartDg
from cassowary.base.functions import get_installed_apps, get_exe_icon
import base64



logger = get_logger(__name__)
wake_base_cmd = 'xfreerdp /d:"{domain}" /u:"{user}" /p:"{passd}" /v:"{ip}" +clipboard /a:drive,root,{share_root} ' \
                '+decorations /cert-ignore /sound /scale:100 /dynamic-resolution /span  ' \
                '/wm-class:"cassowaryApp-echo" /app:"{app}"'


def randomstr(leng=4):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(leng))


def create_desktop_entry(name, comment, exec_path, generic_name, icon, category):
    filename = "cassowaryApp_" + ''.join(e for e in name if e.isalnum())
    template = """[Desktop Entry]
    Comment={comment}
    Encoding=UTF-8
    Exec={exec_path}
    GenericName={generic_name}
    Icon={icon}
    Name[en_US]={name}
    Name={name}
    Categories={category}
    StartupWMClass={wmc}
    StartupNotify=true
    Terminal=false
    Type=Application
    Version=1.0
    X-KDE-RunOnDiscreteGpu=false
    X-KDE-SubstituteUID=false
            """.format(comment=comment, exec_path=exec_path,
                       generic_name=generic_name, name=name,
                       icon=icon, category=category,
                       wmc="cwapp-" + name.replace(" ", ""))
    try:
        desktop_file_path = os.path.join(os.path.expanduser("~"), ".local", "share", "applications",
                                         filename + ".desktop")
        with open(desktop_file_path, "w") as df:
            df.write(template)
        os.popen("update-desktop-database {path}".format(
            path=os.path.join(os.path.expanduser("~"), ".local", "share", "applications")
        ))
        return "Desktop file created successfully !"
    except Exception as e:
        return "Failed to create desktop file ! \n {}".format(str(e))


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
                    except (KeyError, IndexError):
                        pass
            else:
                logger.error("Cannot get network interfaces for domain '%s' ", name)
        except libvirt.libvirtError:
            logger.error("Cannot get ip for '%s' -> %s", name, traceback.format_exc())
        conn.close()
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


def mount_pending(on_complete=None):
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
    if on_complete is not None:
        on_complete()


def unmount_all(on_complete=None):
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
    if on_complete is not None:
        on_complete()


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
        if os.path.exists(path):
            logger.debug("'%s' is a valid absolute full path in fs.. No processing done")
            return None, path
        elif os.path.exists(os.path.join(cfgvars.config["rdp_share_root"], path[1:] if path.startswith("/") else path)):
            rs_path = os.path.join(cfgvars.config["rdp_share_root"], path[1:] if path.startswith("/") else path)
            logger.debug("'%s' is a path mapped to shared root fs, resolving to '%s'", path, rs_path)
            return None, rs_path
        else:
            logger.warning("Requested path '%s' is probably an URL or invalid path.", path)
            logger.debug(cfgvars.config["rdp_share_root"])
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
        if full_path.startswith(cfgvars.config["rdp_share_root"]):
            if full_path == cfgvars.config["rdp_share_root"]:
                return "Z:\\"
            else:
                if cfgvars.config["rdp_share_root"] == "/":
                    return ("Z:" + full_path).replace("/", "\\")
                else:
                    return full_path.replace(cfgvars.config["rdp_share_root"], "Z:").replace("/", "\\")
        else:
            logger.warning("Path '%s' is not a path inside current shared root '%s', and wont be available to guest !")
            return ("Z:" + full_path).replace("/", "\\")
    else:
        return path


def create_reply(message, data, status):
    message["type"] = "response"
    message["status"] = 1 if status else 0
    message["data"] = data
    return message


def full_rdp():
    command = '{rdc} /d:"{domain}" /u:"{user}" /p:"{passd}" /v:{ip} /a:drive,root,{share_root} +auto-reconnect ' \
              '+clipboard /cert-ignore /audio-mode:1 /scale:{scale} /wm-class:"cassowaryApp-FULLSESSION" ' \
              '/dynamic-resolution /{mflag} {rdflag} 1> /dev/null 2>&1 &'
    multimon_enable = int(os.environ.get("RDP_MULTIMON", cfgvars.config["rdp_multimon"]))
    cmd_final = command.format(
        rdflag=cfgvars.config["rdp_flags"],
        domain=cfgvars.config["winvm_hostname"],
        user=cfgvars.config["winvm_username"],
        passd=cfgvars.config["winvm_password"],
        ip=cfgvars.config["host"],
        scale=cfgvars.config["rdp_scale"],
        rdc=cfgvars.config["full_session_client"],
        share_root=cfgvars.config["rdp_share_root"],
        mflag="multimon" if multimon_enable else "span"
    )
    if cfgvars.config["windowed_full_session"]:
        logger.debug("Full session in window mode requested.. span and multimon flags removed !")
        cmd_final = cmd_final.replace(" /"+"multimon" if multimon_enable else "span", "")
    logger.debug("Creating a full RDP session with commandline  : " + command)
    process = subprocess.Popen(["sh", "-c", "{}".format(cmd_final)])
    process.wait()
    logger.debug("Full RDP session ended !")


def vm_state():
    if cfgvars.config["vm_name"].strip() == "":
        return None
    conn = libvirt.open(cfgvars.config["libvirt_uri"])
    if conn is not None:
        try:
            dom = conn.lookupByName(cfgvars.config["vm_name"])
            return int(dom.info()[0])
        except libvirt.libvirtError:
            pass
        conn.close()
    return None


def vm_suspension_handler():
    logger.debug("VM watcher active !")
    logger.debug("VM suspend on inactivity is " + "enabled" if bool(cfgvars.config["vm_auto_suspend"]) else "disabled")
    last_active_on = int(time.time())  # Should at least wait for one timeout
    tc = 0
    vm_app_launch_marker = "/tmp/cassowary-app-launched.state"
    vm_suspend_file = "/tmp/cassowary-vm-state-suspend.state"
    while True:
        if bool(cfgvars.config["vm_auto_suspend"]) and cfgvars.config["vm_name"].strip() != "":
            process = subprocess.check_output(["ps", "auxfww"])
            # Check if any cassowary started freerdp process is running or not
            if len(re.findall(r"freerdp.*\/wm-class:.*cassowaryApp", process.decode())) >= 1 or len(
                    re.findall(r".*cassowary -a", process.decode())) >= 1:
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
                        os.remove(vm_app_launch_marker)  # Delete marker file older than 10 sec
                logger.debug("Suspending VM due to inactivity !")
                conn = libvirt.open(cfgvars.config["libvirt_uri"])
                if conn is not None and bypass is False:
                    try:
                        dom = conn.lookupByName(cfgvars.config["vm_name"])
                        dom.suspend()
                        logger.debug("VM '%s' suspended due to inactivity: ", cfgvars.config["vm_name"])
                        logger.debug("Creating suspension marker file")
                        open(vm_suspend_file, "w").write(str(time.time()))
                        if cfgvars.config["send_suspend_notif"]:
                            os.system('notify-send -u normal --icon \'{icon}\' --app-name Cassowary "VM suspended"'
                                      ' "The VM \'{vm}\' has been suspended due to {delay} seconds of inactivity !"'
                                      .format(icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                                                "gui/extrares/cassowary.png"),
                                              vm=cfgvars.config["vm_name"], delay=cfgvars.config["vm_suspend_delay"]
                                              ))
                    except libvirt.libvirtError:
                        logger.error("Could not suspend vm '%s' -> %s", cfgvars.config["vm_name"],
                                     traceback.format_exc())
                    conn.close()
                else:
                    if conn is not None:
                        logger.error("Cannot connect to libvirt ! at '%s'", cfgvars.config["libvirt_uri"])
                # We also Checked if the vm suspend file exists, if it exists that means we previously suspended VM for
                # inactivity and vm was not resumed by cassowary ! As user may be using VM directly through virt-manager
                # , which we don't want to suspend that session, next suspension happens after next cassowary usage
            else:
                print("Last app launched :", int(time.time()) - last_active_on, " ago, Required : ",
                      cfgvars.config["vm_suspend_delay"], " for suspending. Already suspended: ",
                      os.path.isfile(vm_suspend_file))
            # Else, either the VM was suspended and no cassowary application has been launched since then, or we do not
            # have required inactivity duration, do nothing just wait
        time.sleep(2)
        tc = tc + 2
        if tc >= 10:
            tc = 0
            logger.debug("Refreshing config to update to probable config changes !")
            cfgvars.refresh_config()


def track_new_installations(client):
    while cfgvars.config["scan_new_installs"]:
        status, data = get_installed_apps(client) # Replace with get new installations
        if status is not None:
            for app in data:
                try:
                    name = app[0].split(":")[0]
                    desc = ""
                    version = app[2]
                    path = app[1]
                    parts = app[0].split(":")
                    for part in parts[1:len(parts)]:
                        desc = desc + part + ":"
                    desc = desc[:-1] + " (cassowary remote application)"
                    comment = "'{}' version '{}'".format(name, version)
                    command = "python3 -m cassowary -c guest-run -- '{}' %u".format(
                        path.replace("\\", "\\\\").replace("'", "").replace("\"", ""))
                    ico_status, ico_data = get_exe_icon(client, path)
                    filename = "cassowaryApp_" + ''.join(e for e in name if e.isalnum())
                    icon_path = os.path.join(cfgvars.cache_dir, filename + ".ico")
                    try:
                        if not ico_data == "":
                            with open(icon_path, "wb") as ico_file:
                                ico_file.write(base64.b64decode(ico_data))
                        else:
                            icon_path = cfgvars.config["def_icon"]
                    except KeyError:
                        pass
                    create_desktop_entry(name, comment, command,
                        desc, icon_path, "CasualRDH;Utility;"
                    )
                    logger.debug("Found new installation and created desktop shortcut for '{}'".format(name))
                except AttributeError:
                    logger.warning("Looks like some app returned data that cannot be parsed : %s : %s", str(app),
                                   traceback.format_exc())
        else:
            logger.error("Cannot fetch data for new applications")
        time.sleep(8)


def fix_black_window(forced=False):
    first_launch_track = "/tmp/cassowary-rdp-login-done.state"
    if not os.path.isfile(first_launch_track) or forced:
        # The test window was forced or no other window was opened prevouusly
        logger.debug("Opening & closing a test window to trigger login or try to fix black screen bug on first launch")
        cmd = wake_base_cmd.format(domain=cfgvars.config["winvm_hostname"],
                                   user=cfgvars.config["winvm_username"],
                                   passd=cfgvars.config["winvm_password"],
                                   ip=cfgvars.config["host"],
                                   share_root=cfgvars.config["rdp_share_root"],
                                   app="ipconfig.exe"
                                   )
        logger.debug("Trying to fix black window bug by opening a test window before requested application - " +
                     str(time.time()) + "CMDLINE: " + cmd)
        process = subprocess.Popen(["sh", "-c", "{}".format(cmd)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ts = int(time.time())
        while process.poll() is None:
            for line in process.stdout:
                if "registered device" in line.decode() or int(time.time()) - ts > 10:
                    logger.debug(
                        "App window seems to be created or timeout. Creating marker & Waiting 2 seconds - " + str(
                            time.time()
                        )
                    )
                    open(first_launch_track, "w").write(str(int(time.time())))
                    logger.debug("Created a marker -> One session done")
                    # Create file to remember that one session was already done
                    time.sleep(3)
                    process.kill()
                    break
        logger.debug("Test window opened and closed !")
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
                            "Found suspend state file.. VM was auto suspended previously, clearing it for next session")
                        os.remove(vm_suspend_file)
                    logger.debug("Added 2 sec delay for VM networking to be active !")
                    time.sleep(2)
                    fix_black_window(forced=True)
                elif dom.info()[0] == 5:
                    logger.debug("VM is not running showing a prompt to user")
                    start_dialog = StartDg()
                    start_dialog.run()
                else:
                    logger.warning("VM state is not set to suspended : State -> '%s' ", str(dom.info()[0]))
            except libvirt.libvirtError:
                logger.error("Could not suspend vm '%s' -> %s", cfgvars.config["vm_name"],
                             traceback.format_exc())
            conn.close()
        else:
            logger.error("Cannot connect to libvirt ! at '%s'", cfgvars.config["libvirt_uri"])
    else:
        logger.debug("VM name is blank, maybe not a vm skipping vm resume process !")

# Note: VM suspend file is for preventing suspending vm sessions manually started by user without using cassowary
#        App launcher marker file is prevent vm from suspending right before an app is launched !
