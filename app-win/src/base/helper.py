import random
import string
import os
import time
from .cfgvars import cfgvars


def dialog(body, title=""):
    if os.environ.get("DIALOG_MODE") != "console":
        script = 'x=msgbox("{}" ,0, "{}")'.format(body, title)
        temp_file = os.path.join(cfgvars.tempdir, str(random.randint(11111, 999999)) + ".vbs")
        if not os.path.exists(cfgvars.tempdir):
            os.makedirs(cfgvars.tempdir)
        with open(temp_file, "w") as tmpf:
            tmpf.write(script)
        os.system('wscript.exe ' + temp_file)
        try:
            os.remove(temp_file)
        except OSError:
            pass
    else:
        print(body)


def randomstr(leng=4):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(leng))


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


def create_reply(message, data, status):
    message["type"] = "response"
    message["status"] = 1 if status else 0
    message["data"] = data
    return message

def randomstr(leng=4):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(leng))


def uac_cmd_exec(command, timeout=3, noadmin=False, non_blocking=True):
    temp_file = os.path.join(cfgvars.tempdir, randomstr(8)+ ".vbs")
    script = '''
CreateObject("Shell.Application").ShellExecute "cmd.exe", "/c {command}> {temp_file}.out 2>&1", "", "runas", 1
    '''.format(command=command.replace('"', '""'), temp_file=temp_file.replace('"', '""'))
    if not os.path.exists(cfgvars.tempdir):
        os.makedirs(cfgvars.tempdir)
    if not noadmin:
        with open(temp_file, "w") as tmpf:
            tmpf.write(script)
        os.system('wscript.exe ' + temp_file)
    else:
        if non_blocking:
            os.system("cmd /c {command}> {temp_file}.out 2>&1".format(command=command, temp_file=temp_file))
        else:
            return os.popen(command).read().strip()
    command_exec_at = int(time.time())
    output = None
    while int(time.time()) <= command_exec_at + timeout:
        time.sleep(0.5)
        if os.path.isfile(temp_file + ".out"):
            with open(temp_file + ".out", "r") as tmpf:
                output = tmpf.read()
                if output.strip() != "":
                    break
            try:
                os.remove(temp_file + ".out")
                os.remove(temp_file)
            except OSError:
                pass
    return output
