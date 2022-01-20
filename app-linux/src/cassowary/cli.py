import argparse
import logging
import os
import logging
import sys
import traceback

from .base.log import setup_logging
from .base.helper import path_translate_to_guest
from .base.cfgvars import cfgvars
from PyQt5.QtWidgets import QApplication
from .gui.components.main_ui import MainWindow

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)


    about = """
    #####################################################################################
    #  CasualRDH Client Application (Linux) - Integrate Windows VM with linux hosts     #
    # ---------------------------- Software info ---------------------------------------#
    #      Version     : 0.1A                                                           #
    #      GitHub      : https://github.com/casualsnek/casualrdh                        # 
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
                                casualrdh_linux -a guest-open -- '/home/use/somefile.txt'
                                ( The command is ran directly using RDP without server activity )
    --------------------------------------------------------------------------------------------------------
    guest-run       :   Runs a command on host with parameters either a application on host or guest
                        Usage   :   
                                casualrdh_linux -a guest-run -- 'C:\\..\\vlc.exe' '/home/user/test.mp4'
                                    ( Opens test.mp4 on host with vlc )
                                casualrdh_linux -a guest-run -- '/home/user/flashgame.exe' '-some parameters'
                                ( Runs flashgame.exe located in windows on host with parameters)
                                * The command is ran directly using RDP without server activity 
    --------------------------------------------------------------------------------------------------------                                
    raw-cmd         :   Sends a raw command to the windows server . Parameters is list of server commands
                        and their parameters. (Requires at least one active RDP session)
                        (Path translations will not be done)
                        Usage   :
                                casualrdh_linux -a raw-cmd -- run /usr/sbin/firefox
                                ( This sends command to server to request host to launch firefox)
                                casualrdh_linux -a raw-cmd -- add-drive-share Y y_share
                                ( This sends command to server share local disk Y with share name y_share)
    --------------------------------------------------------------------------------------------------------                                
    path-map        :   Maps the given input to path on huest windows install using cached share info
                        If it is not a valid local path input is be returned as it is
                        Usage   :
                                casualrdh_linux -a path-map -- /home/user/document/personal.docx
    """
    BASE_RDP_CMD = 'xfreerdp {rdflag} /d:"{domain}" /u:"{user}" /p:"{passd}" /v:{ip} +auto-reconnect +clipboard ' \
                   '+home-drive -wallpaper /scale:{scale} /dynamic-resolution /{mflag} /wm-class:"{wmclass}" ' \
                   '/app:"{execu}" /app-icon:"{icon}"'
    parser = argparse.ArgumentParser(description=about, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-bc', '--background-client', dest='server',
                        help='Create a client which listens for host forwarded requests and replies them',
                        action='store_true')
    parser.add_argument('-a', '--gui-application', dest='guiapp',
                        help='Launch casualRDH Configuration GUI',
                        action='store_true')
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
        exit(1)
    if args.command_help:
        print(about+"\n"+action_help)
    if args.server:
        # start_server(cfgvars.config["host"], cfgvars.config["port"])
        pass
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
                response = {"status": False}
                if args.command == "path-map":
                    print(path_translate_to_guest(args.cmdline[0]))
                elif args.command == "guest-run":
                    translated_paths = [path_translate_to_guest(argument) for argument in args.cmdline]
                    # Check and translated every argument if it is a path
                    wm_class = args.wmclass
                    icon = args.icon
                    multimon_enable = int(os.environ.get("RDP_MULTIMON", cfgvars.config["rdp_multimon"]))
                    if wm_class is None:
                        wm_class = os.environ.get("WM_CLASS", "casualrdhApp-"+args.cmdline[0].split("/")[-1].split("\\")[-1])
                    if icon is None:
                        icon = os.environ.get("APP_ICON", cfgvars.config["def_icon"])
                    cmd = BASE_RDP_CMD.format(rdflag=cfgvars.config["rdp_flags"], domain=cfgvars.config["winvm_hostname"],
                                              user=cfgvars.config["winvm_hostname"], passd=cfgvars.config["winvm_password"],
                                              ip=cfgvars.config["host"], scale=cfgvars.config["rdp_scale"],
                                              mflag="multimon" if multimon_enable else "span", wmclass=wm_class,
                                              execu=args.cmdline[0], icon=icon)

                    if len(translated_paths) > 1:
                        rd_app_args = ""
                        for path in translated_paths[1:]:
                            if " " in path:
                                path = '"{}"'.format(path)
                            rd_app_args = rd_app_args+path+" "
                        cmd = cmd+'/app-cmd:"{}"'.format(rd_app_args.strip())
                    print(cmd+" 1> /dev/null 2>&1 &")
                elif args.command == "raw-cmd":
                    # response = client.send_wait_response(args.cmdline, timeout=10)
                    print(args)
                else:
                    print("'{}' is not a supported command".format(args.command), "Unsupported command")
        except Exception as e:
            logger.error("Unexpected error: Exception: %s, Traceback : %s", str(e), traceback.format_exc())
            print("Unexpected error.. Exiting")
