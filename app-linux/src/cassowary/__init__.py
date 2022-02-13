import argparse
import os
import subprocess
import sys
import traceback
import time
from .base.log import get_logger
from .base.helper import path_translate_to_guest, vm_suspension_handler, full_rdp, vm_wake, fix_black_window, vm_state
from .base.cfgvars import cfgvars
from PyQt5.QtWidgets import QApplication
from .gui.components.main_ui import MainWindow
from .client import Client
import threading



def main():
    logger = get_logger(__name__)
    cfgvars.app_root = os.path.dirname(os.path.realpath(__file__))

    def start_bg_client(reconnect=True):
        vm_watcher = threading.Thread(target=vm_suspension_handler)
        vm_watcher.daemon = True
        vm_watcher.start()
        logger.info("Connecting to server....")
        while True:
            try:
                using_host = cfgvars.config["host"]
                client_ = Client(using_host, cfgvars.config["port"])
                client_.init_connection()
                client_.accepting_forwards = True
                logger.info("Connected to server !")
                response = client_.send_wait_response(["declare-self-host"], timeout=5)
                if response is not False:
                    status, data = response["status"], response["data"]
                    if status:
                        logger.info("Declared self as host system client to the server")
                        # Now everything should be done by sender and receiver thread,
                        # We just wait here to check if anything has stopped in client object, if yes, recreate client
                        # and try again
                        while True:
                            if not client_.sender.is_alive() or not client_.receiver.is_alive()\
                                    or client_.stop_connecting or using_host != cfgvars.config["host"]\
                                    or vm_state() in [4, 5]:
                                logger.debug("Connection seems to be lost or vm info got changed in config or vm turned off")
                                break
                            else:
                                logger.info("Connected to server")
                            time.sleep(5)
                    else:
                        logger.info(
                        "Failed to declare self host.. Retrying after 5 seconds. Server response: {}, {}".format(status,
                                                                                                                 data))
                logger.info("Server error: {}".format(response))
                client_.die()
            except KeyboardInterrupt:
                logger.info("Got keyboard interrupt.. Exiting")
                break
            except Exception as e:
                logger.error("Ignored exception: '%s', reconnecting to server after 5 seconds", traceback.format_exc())
            time.sleep(5)
            if not reconnect:
                logger.warning("Reconnect is enabled, client is stopped")
                break

    about = """
    #####################################################################################
    #  cassowary Client Application (Linux) - Integrate Windows VM with linux hosts     #
    # ---------------------------- Software info ---------------------------------------#
    #      Version     : 0.5A                                                           #
    #      GitHub      : https://github.com/casualsnek/cassowary                        # 
    #      License     : GPLv2                                                          #
    #      Maintainer  : @casualsnek (Github)                                           #
    #      Email       : casualsnek@pm.me                                               #
    #####################################################################################

    """
    action_help = """
    This tool itself does not do much, use 'raw-cmd' action and pass commands list as 
    proper json While using any command put "--" after command name to pass arguments 
    starting with dash (-)
    --------------------------------------------------------------------------------------------------------
    Command         :             Description
    --------------------------------------------------------------------------------------------------------
    guest-open      :   Open a file with default application on guest.
                        Only takes one file path as parameter
                        Usage   :
                                cassowary -c guest-open -- '/home/use/somefile.txt'
                                ( The command is ran directly using RDP without server activity )
    --------------------------------------------------------------------------------------------------------
    guest-run       :   Runs a command on host with parameters either a application on host or guest
                        Usage   :   
                                cassowary -c guest-run -- 'C:\\..\\vlc.exe' '/home/user/test.mp4'
                                    ( Opens test.mp4 on host with vlc )
                                cassowary -c guest-run -- '/home/user/flashgame.exe' '-some parameters'
                                ( Runs flashgame.exe located in windows on host with parameters)
                                * The command is ran directly using RDP without server activity 
    --------------------------------------------------------------------------------------------------------                                
    raw-cmd         :   Sends a raw command to the windows server . Parameters is list of server commands
                        and their parameters. (Requires at least one active RDP session)
                        (Path translations will not be done)
                        Usage   :
                                cassowary -c raw-cmd -- run /usr/sbin/firefox
                                ( This sends command to server to request host to launch firefox)
                                cassowary -c raw-cmd -- add-drive-share Y y_share
                                ( This sends command to server share local disk Y with share name y_share)
    --------------------------------------------------------------------------------------------------------                                
    path-map        :   Maps the given input to path on guest windows install using cached share info
                        If it is not a valid local path input is be returned as it is
                        Usage   :
                                cassowary -c path-map -- /home/user/document/personal.docx
    """
    BASE_RDP_CMD = '{rdc} /d:"{domain}" /u:"{user}" /p:"{passd}" /v:{ip} +clipboard /a:drive,root,{share_root} ' \
                   '+decorations /cert-ignore /sound /scale:{scale} /dynamic-resolution /{mflag} {rdflag} ' \
                   '/wm-class:"{wmclass}" ' \
                   '/app:"{execu}" /app-icon:"{icon}" '
    parser = argparse.ArgumentParser(description=about, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-bc', '--background-client', dest='bgc',
                        help='Create a client which listens for host forwarded requests and replies them',
                        action='store_true')
    parser.add_argument('-a', '--gui-application', dest='guiapp',
                        help='Launch cassowary Configuration GUI',
                        action='store_true')
    parser.add_argument('-f', '--full-session', dest='fullsession', help='Launches full rdp session', action='store_true')
    parser.add_argument('-np', '--no-polkit', dest='nopkexec', help='Prints messages in console, uses xterm with sudo'
                                                                    'instead of polkit pkexec for root access',
                        action='store_true')
    parser.add_argument('-wc', '--wm-class', dest='wmclass', help='Window manager class for guest-run/guest-open',
                        default=None)
    parser.add_argument('-ic', '--icon', dest='icon', help='Application icon of RDP apps for Window Manager',
                        default=None)
    parser.add_argument('-c', '--command', dest='command', help='The command to run (use -ch) for help')
    parser.add_argument('-ch', '--command-help',
                        dest='command_help',
                        help='Shows available commands and its description and few example usages',
                        action='store_true')
    parser.add_argument('cmdline',
                        nargs='*',
                        help="Arguments for the used command",
                        default=None
                        )
    args = parser.parse_args()
    if args.nopkexec:
        os.environ["DIALOG_MODE"] = "console"
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    if args.command_help:
        print(about + "\n" + action_help)
    if args.bgc:
        start_bg_client()
    if args.fullsession:
        vm_wake()
        full_rdp()
        sys.exit(0)
    if args.guiapp:
        logger.debug("Starting configuration GUI")
        app = QApplication(sys.argv)
        cfgvars.refresh_config()
        mainui = MainWindow()
        mainui.show()
        app.exec_()
    else:
        try:
            if not args.cmdline:
                print("At least one argument is required, exiting..")
                exit(1)
            else:
                wm_class = args.wmclass
                icon = args.icon
                multimon_enable = int(os.environ.get("RDP_MULTIMON", cfgvars.config["rdp_multimon"]))
                if wm_class is None:
                    wm_class = os.environ.get("WM_CLASS",
                                              "cassowaryApp-" + args.cmdline[0].split("/")[-1].split("\\")[-1])
                if icon is None:
                    icon = os.environ.get("APP_ICON", cfgvars.config["def_icon"])
                response = {"status": False}
                if args.command == "path-map":
                    print(path_translate_to_guest(args.cmdline[0]))
                elif args.command == "guest-run":
                    translated_paths = [path_translate_to_guest(argument) for argument in args.cmdline]
                    print(translated_paths)
                    # Check and translated every argument if it is a path
                    cmd = BASE_RDP_CMD.format(rdflag=cfgvars.config["rdp_flags"],
                                              domain=cfgvars.config["winvm_hostname"],
                                              user=cfgvars.config["winvm_username"],
                                              passd=cfgvars.config["winvm_password"],
                                              ip=cfgvars.config["host"], scale=cfgvars.config["rdp_scale"],
                                              mflag="multimon" if multimon_enable else "span", wmclass=wm_class,
                                              rdc=cfgvars.config["app_session_client"],
                                              share_root=cfgvars.config["rdp_share_root"],
                                              execu=args.cmdline[0], icon=icon)

                    if len(translated_paths) > 1:
                        rd_app_args = ""
                        for path in translated_paths[1:]:
                            if " " in path:
                                # This looks ugly because windows uses "" for escaping " instead of \" and this is the
                                # only way i found so far
                                path = '\\"\\"\\"{}\\"\\"\\"'.format(path)
                            rd_app_args = rd_app_args + path + " "
                        # Now problem for path with spaces is solved, but the path pointing to drive's root
                        #                               | DO NOT REMOVE THIS SPACE or else path pointing to drive letter
                        #                      |--------| (C:| or D:| ) will not launch due to \ at end escaping the
                        #                      V        | ending quote
                        cmd = cmd + '/app-cmd:"{} "'.format(rd_app_args.strip())
                    #cmd = cmd + " 1> /dev/null 2>&1 &"
                    app = QApplication(sys.argv)
                    vm_wake()
                    fix_black_window()
                    logger.debug("guest-run with commandline: "+cmd)
                    process = subprocess.Popen(["sh", "-c", "{}".format(cmd)])
                    process.wait()
                elif args.command == "guest-open":
                    path = path_translate_to_guest(args.cmdline[0])
                    if " " in path:
                        # This looks ugly because windows uses "" for escaping " instead of \" and this is the
                        # only way i found so far
                        path = '\\"\\"\\"{}\\"\\"\\"'.format(path)
                    cmd = BASE_RDP_CMD.format(rdflag=cfgvars.config["rdp_flags"],
                                              domain=cfgvars.config["winvm_hostname"],
                                              user=cfgvars.config["winvm_username"],
                                              passd=cfgvars.config["winvm_password"],
                                              ip=cfgvars.config["host"], scale=cfgvars.config["rdp_scale"],
                                              mflag="multimon" if multimon_enable else "span", wmclass=wm_class,
                                              rdc=cfgvars.config["app_session_client"],
                                              share_root=cfgvars.config["rdp_share_root"],
                                              execu="cmd.exe", icon=icon)
                    cmd = cmd + '/app-cmd:"/c explorer.exe {} "'.format(path)
                    app = QApplication(sys.argv)
                    vm_wake()
                    fix_black_window()
                    logger.debug("guest-open with commandline: " + cmd)
                    process = subprocess.Popen(["sh", "-c", "{}".format(cmd)])
                    process.wait()
                elif args.command == "raw-cmd":
                    vm_wake()
                    client__ = Client(cfgvars.config["host"], cfgvars.config["port"])
                    client__.init_connection()
                    response = client__.send_wait_response(args.cmdline, timeout=10)
                    print(response)
                else:
                    print("'{}' is not a supported command".format(args.command), "Unsupported command")
        except Exception as e:
            logger.error("Unexpected error: Exception: %s, Traceback : %s", str(e), traceback.format_exc())
            sys.exit(1)
    sys.exit(0)
