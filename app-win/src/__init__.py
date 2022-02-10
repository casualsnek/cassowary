import argparse
import logging
import os
import sys
from base.command import register_all
from server import *
from client import Client
from base.cfgvars import cfgvars
from base.helper import dialog


if __name__ == "__main__":
    about = """
    #####################################################################################
    #  cassowary Server/Client App (Windows) - Integrate Windows VM with linux hosts    #
    # ---------------------------- Software info ---------------------------------------#
    #      Version     : 0.5A                                                           #
    #      GitHub      : https://github.com/casualsnek/cassowary                        # 
    #      License     : GPLv2                                                          #
    #      Maintainer  : @casualsnek (Github)                                           #
    #      Email       : casualsnek@pm.me                                               #
    #####################################################################################
      
    """
    action_help = """
    This tool itself does not do much, use 'raw-cmd' action and pass commands list as proper json
    While using any command put "--" after command name to pass arguments starting with dash (-)
    --------------------------------------------------------------------------------------------------------
    Command         :             Description
    --------------------------------------------------------------------------------------------------------
    xdg-open        :   Open a file with 'xdg-open' on host, Used for opening file with default 
                        application for file type on host. Only takes one file path as parameter
                        Usage   : 
                                cassowary -c xdg-open -- 'C:\\Users\\Cas\\test.mp4'
    --------------------------------------------------------------------------------------------------------
    run-cmd         :   Runs a command on host with parameters either a application on host or guest
                        Usage   :
                                cassowary -c run-cmd -- '/usr/bin/mpv' 'C:\\Users\\Cas\\test.mp4'
                                ( Opens test.mp4 on host with mpv )
                                cassowary -c run-cmd -- 'C:\\linuxbin.run' '-some parameters'
                                ( Runs linuxbin.run located in windows on host with parameters)
    --------------------------------------------------------------------------------------------------------                                
    raw-cmd         :   Sends a raw command to the server application. Parameters is list of server commands
                        and their parameters. (Path translations will not be done)
                        Usage   :
                                cassowary -c raw-cmd -- fwd-host run /usr/sbin/firefox
                                ( This sends command to server to request host to launch firefox)
                                cassowary -c raw-cmd -- add-drive-share Y y_share
                                ( This sends command to server share local disk Y with share name y_share)
    """
    parser = argparse.ArgumentParser(description=about, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-s', '--start-server', dest='server', help='Starts a server instance listening for connections',
                        action='store_true')
    parser.add_argument('-nk', '--no-kill', dest='nokill',
                        help='Starts a server instance listening for connections',
                        action='store_true')
    parser.add_argument('-np', '--no-popup', dest='nopopup', help='Prints to console instead of showing popup on error',
                        action='store_true')
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
    if args.nopopup:
        os.environ["DIALOG_MODE"] = "console"
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    register_all()
    if args.command_help:
        print(about+"\n"+action_help)
    if args.server:
        while True:
            try:
                start_server(cfgvars.config["host"], cfgvars.config["port"])
                sys.exit(0)
            except OSError as e:
                if "[WinError 10048]" in str(e):
                    if not args.nokill:
                        pid = os.popen("netstat -ano | findstr :{}".format(cfgvars.config["port"])).read().strip().split()[-1]
                        os.popen("taskkill /pid {} /f".format(pid))
                    else:
                        break
                else:
                    break
    else:
        if not args.cmdline:
            print("At least one argument is required, exiting..")
            sys.exit(1)
        else:
            client = Client(port=cfgvars.config["port"])
            client.init_connection()
            response = {"status":False}
            if args.command == "xdg-open":
                # Use DriveShareHelper use its path_on_host method to translate probable path strings to linux paths
                status, host_path = cfgvars.commands_handlers["dircommands"].path_on_host(args.cmdline[0])
                message = host_path
                # False status means path is inaccessible from host, None means it's either
                # not a path (maybe URL ??) or linux path
                if status is not False:
                    # Now send request to server to send request to host and forward us the host's response
                    # TODO: Uncomment these
                    response = client.send_wait_response(["fwd-host", "xdg-open", host_path], timeout=20)
                    if response is not False:
                        print(response["data"])
                    else:
                        message = "Server sent no reply"
                if status is False or bool(response["status"]) is False:
                    dialog(
                        "{} (File path: {})".format(message, args.cmdline[0]),
                        "cassowary client 'xdg-open' failed"
                    )
            elif args.command == "open-host-term":
                # Use DriveShareHelper use its path_on_host method to translate probable path strings to linux paths
                status, host_path = cfgvars.commands_handlers["dircommands"].path_on_host(args.cmdline[0])
                message = host_path
                # False status means path is inaccessible from host, None means it's either
                # not a path (maybe URL ??) or linux path
                if status is not False:
                    # Now send request to server to send request to host and forward us the host's response
                    # TODO: Uncomment these
                    response = client.send_wait_response(["fwd-host", "open-term-at", host_path], timeout=20)
                    if response is not False:
                        print(response["data"])
                    else:
                        message = "Server sent no reply"
                if status is False or bool(response["status"]) is False:
                    dialog(
                        "{} (File path: {})".format(message, args.cmdline[0]),
                        "cassowary client 'open-host-term' failed"
                    )
            elif args.command == "host-run":
                # Each argument can be a windows path, convert the path to linux path if it is a windows path
                # and the location presented by path exists
                translated_cmds = []
                status = False
                message = ""
                for arg in args.cmdline:
                    status, host_path = cfgvars.cfgvars.commands_handlers["dircommands"].path_on_host(arg)
                    message = host_path
                    if status is False:
                        break
                    translated_cmds.append(host_path)
                if status is not False:
                    response = client.send_wait_response(["fwd-host", "run"] + translated_cmds, timeout=20)
                    if response is not False:
                        if response["status"] is True:
                            print("The command '{}' will now be executed on host").format(
                                " ".join(i for i in translated_cmds)
                            )
                        else:
                            message = response["data"]
                    else:
                        status = False
                        message = "Server sent no reply, make sure server is active"
                if status is False or bool(response["status"]) is False:
                        dialog(
                            "{}".format(message),
                            "cassowary client 'host-run' failed"
                        )
            elif args.command == "raw-cmd":
                response = client.send_wait_response(args.cmdline, timeout=10)
                print(response)
            else:
                dialog("'{}' is not a supported command".format(args.command), "Unsupported command")
            client.die()
    sys.exit(0)