import sys
import time
from base.cfgvars import cfgvars
from base.log import get_logger
from base.helper import create_reply, randomstr
import threading
import socket
import json
import traceback

logger = get_logger(__name__)


class ClientConnectionThread():
    def __init__(self, name, session, address):
        self.name = name
        logger.debug("[ClientID: %s] New client connected", self.name)
        self.session = session  # Socket connection to client
        self.address = address  # Client Address
        self.__cmd_responses = {}  # All "response" message types, key of dict is message's 'id' field
        self.__send_queue = []  # Message that are to be sent back to client, polled by self.__send() method
        self.__response_storage_lifespan = 360  # Max time (seconds) after which response is deleted from _cmd_responses
        self.__use_host_send_queue = False  # If true also send fwd-host messages to client from self.__send() method
        self.stop_listening = False  # If set to true self.__send() and self.__receive() will stop and terminate
        self.__eom = cfgvars.config["eom"]
        # Str which denotes end of a  message block, must be same on client and server
        self.host_fwd_timeout = 20  # Time for which messages queued for will be waited for execution before removal

    def __send_host_response(self, message):
        message_id = message["id"]
        logger.info("[ClientID: %s] Forwarding message to host client: MSG_ID: %s", self.name, message_id)
        cfgvars.cmd_queue_host_only.append(message)
        cfgvars.cmd_host_only_ids.append(message_id)
        sent_at = int(time.time())
        logger.debug("[ClientID: %s] Waiting for reply from host: MSG_ID: %s", self.name, message_id)
        while int(time.time()) < sent_at + self.host_fwd_timeout:
            if message_id in cfgvars.cmd_host_only_responses:
                self.__send_queue.append(create_reply(
                    message,
                    cfgvars.cmd_host_only_responses[message_id]["data"],
                    cfgvars.cmd_host_only_responses[message_id]["status"]
                ))
                logger.error("[ClientID: %s] Host replied to message : MSG_ID: %s", self.name, message_id)
                cfgvars.cmd_host_only_responses.pop(message_id)
                return True
            time.sleep(1)
        # We timed out, no response from host, remove the message from queue and send client message that it failed
        if message in cfgvars.cmd_queue_host_only:
            cfgvars.cmd_queue_host_only.remove(message)
        cfgvars.cmd_host_only_ids.remove(message_id)
        logger.error("[ClientID: %s] Host send no reply for message: MSG_ID: %s", self.name, message_id)
        self.__send_queue.append(create_reply(
            message,
            "No response from host. Timed out after : {} seconds".format(self.host_fwd_timeout),
            False
        ))
        return False

    # Use loop and thread instead of just a send call because this not only sends message but also checks if any client
    # have left message for host client too, we we don't constantly look for message to host, maybe the file requested
    # to be opened on host system will open after an hour or more !
    def __send(self):
        while not self.stop_listening:
            try:
                for message in self.__send_queue:
                    logger.debug("[ClientID: %s] Got message in queue. MSG_ID: %s", self.name, message["id"])
                    # Send pending message to client itself, mostly response of request made by client
                    message_json = json.dumps(message) + self.__eom
                    self.session.sendall(message_json.encode())
                    logger.info("[ClientID: %s] Sent message to client. MSG_ID: %s", self.name, message["id"])
                    self.__send_queue.remove(message)
                # If client also accepts message from host only queue (message from other clients to this client, which
                # identifies as host system )
                if self.__use_host_send_queue:
                    for message in cfgvars.cmd_queue_host_only:
                        message_json = json.dumps(message) + self.__eom
                        self.session.sendall(message_json.encode())
                        logger.info(
                            "[ClientID: %s] Client is host, Fwding host only messages. MSG_ID: %s",
                            self.name, message["id"]
                        )
                        cfgvars.cmd_queue_host_only.remove(message)
                time.sleep(0.01)
            except (ConnectionResetError, KeyboardInterrupt):
                self.stop_listening = True
            except:
                logger.error("[ClientID: %s] Unknown error while listening for messages: `%s`", traceback.format_exc())
                self.stop_listening = True
                self.session.close()
        logger.debug("[ClientID: %s] Sender is exiting ", self.name)
        return True

    def __receive(self):
        while not self.stop_listening:
            message = b""
            while not self.stop_listening:
                try:
                    message = message + self.session.recv(16000)
                    if message.endswith(self.__eom.encode()) or message == b"":
                        break
                except (ConnectionResetError, KeyboardInterrupt):
                    logger.error("[Client: %s] Client disconnected or keyboard interrupt received", self.name)
                    self.stop_listening = True
                except:
                    logger.error("[ClientID: %s] Unknown error while listening for messages: `%s`", self.name,
                                 traceback.format_exc())
                    self.stop_listening = True
                    self.session.close()

            if message == b"" or self.stop_listening:
                self.stop_listening = True
                self.session.close()
                break
            try:
                message = json.loads(message.decode("utf-8").replace(self.__eom, ""))
                if message["type"] == "response":
                    logger.info("[ClientID: %s] Received a response to message : MSG_ID: %s", self.name, message["id"])
                    message["received_on"] = int(time.time())
                    if message["id"] in cfgvars.cmd_host_only_ids:
                        # This is a reply to command requested by different client, put it in globally
                        # accessible variable
                        print("Got a reply to host forwarded message")
                        cfgvars.cmd_host_only_responses[message["id"]] = message
                        cfgvars.cmd_host_only_ids.remove(message["id"])
                    else:
                        self.__cmd_responses[message["id"]] = message
                elif message["type"] == "request":
                    logger.info("[ClientID: %s] Received a request : MSG_ID: %s", self.name, message["id"])
                    if message["command"][0] == "fwd-host":
                        logger.info("[ClientID: %s] Received a forward to host request : MSG_ID: %s", self.name,
                                    message["id"])
                        # Send message to host, wait for host response, send response back to this client
                        # But first remove fwd-host command before sending to host else it will fail
                        message["command"].pop(0)
                        self.__send_host_response(message)
                    elif message["command"][0] == "declare-self-host":
                        self.__use_host_send_queue = True
                        logger.info("[ClientID: %s] Declared itself as host.. "
                                    "This client will now receive messages forwarded to host", self.name)
                        self.__send_queue.append(create_reply(
                            message,
                            "This client will now receive messages forwarded to host",
                            True
                        ))
                    elif message["command"][0] in cfgvars.commands:
                        # A valid command to run was received,  run the command and put response to send queue
                        # Which will be sent back to client
                        logger.info("[ClientID: %s] Request handled by : %s", self.name,
                                    cfgvars.commands[message["command"][0]])
                        handler_name = cfgvars.commands[message["command"][0]]
                        status, data = cfgvars.commands_handlers[handler_name].run_cmd(message["command"])
                        self.__send_queue.append(create_reply(message, data, status))
                    else:
                        # This is unsupported command, send the reply back to client
                        logger.debug("[ClientID: %s] Got unsupported command: Message body: `%s`", self.name, message)
                        self.__send_queue.append(create_reply(
                            message,
                            "No instruction for command: '{}' ".format(message["command"][0]),
                            False
                        ))
                else:
                    logger.debug("[ClientID: %s] Message type error: Message body: `%s`", self.name, message)
                    self.__send_queue.append(create_reply(
                        message,
                        "Unsupported message type: '{}' ".format(message["type"]),
                        False
                    ))
            except (json.JSONDecodeError, KeyError, IndexError):
                logger.error("[ClientID: %s] Received a deformed message. Message body : '%s', Traceback : %s",
                             self.name,
                             message,
                             traceback.format_exc()
                             )
                self.__send_queue.append(create_reply(
                    {"id": "--", "type": "response"},
                    "Invalid message format",
                    False
                ))
            except Exception as e:
                logger.error("[ClientID: %s] Unknown error while listening for messages: `%s`", self.name,
                             traceback.format_exc())
                self.stop_listening = True
                self.session.close()
        logger.debug("[ClientID: %s] Receiver is exiting ", self.name)
        return True

    def run(self):
        receiver = threading.Thread(target=self.__receive)
        sender = threading.Thread(target=self.__send)
        receiver.daemon = True
        sender.daemon = True
        # Start Threads
        receiver.start()
        sender.start()


def start_server(host, port):
    try:
        server = socket.socket()
        server.settimeout(3)
        server.bind((host, port))
        server.listen(5)
        clients = []
        while True:
            try:
                session, address = server.accept()
                clients.append(ClientConnectionThread(randomstr(8), session, address))
                clients[len(clients) - 1].run()
                # Now check if any client has paused the work and remove them
                for client in clients:
                    if client.stop_listening:
                        logger.debug("Client Thread '%s' has stopped listening, removing it", client.name)
                        del clients[clients.index(client)]
            except socket.timeout:
                pass
    except KeyboardInterrupt:
        logger.debug("Got keyboard interrupt")
    if server is not None:
        server.close()
    logger.info("Server is stopping !")
    sys.exit(1)
