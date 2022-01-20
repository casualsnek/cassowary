import socket
import json
import threading
import time
import traceback
from base.log import get_logger
from base.cfgvars import cfgvars
from base.helper import create_reply, create_request
import logging

logger = get_logger(__name__)


class Client:
    def __init__(self, host="127.0.0.1", port=7220):
        self.send_queue = []
        self.cmd_responses = {}
        self.stop_connecting = False
        self.__eom = cfgvars.config["eom"]
        self.__host = host
        self.__port = port
        self.server = None
        self.sender = None
        self.receiver = None

    def die(self):
        logger.info("Attempting to stop client activity")
        self.stop_connecting = True
        if self.server is not None:
            self.server.close()

    def init_connection(self):
        logger.info("Attempting to connect to server")
        if self.server is not None:
            self.server.close()

        # Stop threads if active
        if self.sender is not None:
            logger.debug("Sender thread seems already initialised")
            if self.sender.is_alive():
                logger.warning("Sender thread is still alive, waiting for termination")
                self.stop_connecting = True
                self.sender.join(3)
        if self.receiver is not None:
            logger.debug("Receiver thread seems already initialised")
            if self.receiver.is_alive():
                logger.warning("Receiver thread is still alive, waiting for termination")
                self.stop_connecting = True
                self.receiver.join(3)
        # Re create socket connection
        logger.debug("Creating new connection")
        self.server = socket.socket()
        self.server.settimeout(5)
        print(self.__host, self.__port)
        self.server.connect(("127.0.0.1", self.__port))
        self.server.settimeout(None)
        logger.info("Connected to server at {}:{}".format(self.__host, self.__port))

        # Start threads
        logger.debug("Starting sender and receiver threads")
        self.__create_sub_threads()

    def __receive(self):
        logger.debug("Receiver up")
        while not self.stop_connecting:
            message = b""
            while not self.stop_connecting:
                try:
                    recent_msg = self.server.recv(10000000)
                    message = message + recent_msg
                except Exception as e:
                    logger.error("Error receiving messages, Exception- %s, Traceback : %s", str(e),
                                 traceback.format_exc())
                    self.stop_connecting = True
                    break
                if message.endswith(self.__eom.encode()) or message == b"":
                    break
            if message == b"" or self.stop_connecting:
                self.stop_connecting = True
                self.server.close()
                break
            try:
                message = json.loads(message.decode("utf-8").replace(self.__eom, ""))
                if message["type"] == "response":
                    message["received_on"] = int(time.time())
                    self.cmd_responses[message["id"]] = message
                else:
                    self.send_queue.append(create_reply(
                        message,
                        "Windows client does not support this message type: '{}' ".format(message["type"]),
                        False
                    ))
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error("Client received a deformed message. Message body: %s", str(message))
        logger.debug("Stopping receive sub-thread... (%s)", str(self.stop_connecting))

    def __send(self):
        logger.debug("Sender up")
        while not self.stop_connecting:
            for message in self.send_queue:
                try:
                    message_json = json.dumps(message) + self.__eom
                    self.server.sendall(message_json.encode())
                    self.send_queue.remove(message)
                except Exception as e:
                    logger.error("Error receiving messages, Exception- %s, Traceback : %s", str(e),
                                 traceback.format_exc())
                    self.stop_connecting = True
            time.sleep(0.01)
        logger.debug("Stopping send sub-thread... (%s)", str(self.stop_connecting))

    # These request_enqueue, get_response_of are here if user manually want to send request or get response at any time
    # Else send_wait_response can be used which waits for response till timeout and returns response

    def request_enqueue(self, command_list):
        message = create_request(command_list)
        if self.sender is not None:
            if self.sender.is_alive():
                # Sender is alive so, add to queue
                self.send_queue.append(message)
        return message

    def get_response_of(self, message_id):
        if message_id in self.cmd_responses:
            response = self.cmd_responses[message_id]
            self.cmd_responses.pop(message_id)
            return response
        else:
            return False

    def send_wait_response(self, command_list, timeout=10):
        if self.receiver is not None:
            if self.receiver.is_alive():
                message = create_request(command_list)
                self.send_queue.append(message)
                sent_at = int(time.time())
                wait_till = sent_at + timeout
                while int(time.time()) < wait_till:
                    response = self.get_response_of(message["id"])
                    if response:
                        return response
                try:
                    self.send_queue.remove(message)
                except ValueError:
                    logger.error("Value error while waiting for response. Traceback : %s", traceback.format_exc())
                    pass
                return False
        return {"status": 0, "data": "Not connected to server", "command": []}

    def __create_sub_threads(self):
        self.stop_connecting = False
        self.sender = threading.Thread(target=self.__send)
        self.sender.daemon = True
        self.receiver = threading.Thread(target=self.__receive)
        self.receiver.daemon = True
        self.sender.start()
        self.receiver.start()
