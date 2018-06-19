#!/usr/bin/env python

from json import load
import logging
import re
from select import select
import socket
import time
from threading import Thread

BUFFER_SIZE = 100

# Set the format for log messages (warnings, errors, etc.)
LOG_FORMAT = "[%(levelname)s] [%(msecs)d] [%(threadName)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT)
logging.getLogger().setLevel(logging.INFO)


class MackerelClient:

    def __init__(self, name, type_):
        self.name = name
        self.type = type_
        self.ip = None
        self.port = None
        self.socket = None

        self.running = False

        self.protocol = load(open("protocol.json"))

    def connect(self):
        """
        Attempt to establish a connection with server.
        """
        self.socket = None
        if not (self.ip and self.port):
            if not self.ip:
                logging.error("IP address not set.")
            if not self.port:
                logging.error("Port not set.")
            return

        try:
            s = socket.socket()
            s.settimeout(5)
            s.connect((self.ip, self.port))
        except Exception as e:
            logging.error("Connection to %s:%d failed: error %d (%s)",
                          self.ip, self.port, e.errno, e.strerror)
            return
        else:
            self.socket = s

        if self.socket:
            logging.info("Found socket on %s:%d", self.ip, self.port)

            logging.info("Beginning handshake")
            data = self.safe_read()
            if data == 'WHOIS':
                resp = "{0};{1}\n".format(self.name, self.type)
                self.safe_send(resp)

            data = self.safe_read()
            self.handle_output(data)
        else:
            logging.error("No socket found.")
            return

    def run(self):
        if not self.socket:
            logging.warning("Attempting to run without a connection, "
                            "ignoring...")
        else:
            ioloop = Thread(target=self.io, name="IO")
            watcher = Thread(target=self.watch, name="WATCHER")

            ioloop.start()
            watcher.start()

        while self.running:
            pass

        logging.warning("Shutting down...")

    def watch(self):
        """
        Watch for incoming input from server.
        """
        while self.running:
            time.sleep(0.1)
            if self.socket and self.socket.fileno() >= 0:
                has_data, _, _ = select([self.socket], [], [], 1)
                if has_data:
                    data = self.safe_read()
                    self.handle_output(data)

    def io(self):
        """
        Run basic I/O loop.
        """
        while self.running:
            msg = input('> ')
            self.run_command(msg)

    def valid_command(self, cmd):
        """
        Check command syntax.
        """
        # TODO Make error messages more descriptive.
        tokens = cmd.split(';')
        basecmd, args = tokens[0], tokens[1:]

        if basecmd not in self.protocol.keys():
            logging.error("Invalid command.")
            return False
        else:
            spec = self.protocol[basecmd]
            if spec["type"] != "any" and spec["type"] != self.type:
                logging.error("Invalid command for this node type.")
                return False
            if not (spec['min_args'] <= len(args) <= spec['max_args']):
                logging.error("Invalid number of arguments.")
                return False
            if not all(re.match(regex, arg) for regex, arg
                       in zip(spec["arg_formats"], args)):
                logging.error("Invalid argument format.")
                return False

        return True

    def handle_output(self, resp):
        """
        Parse output from server.
        """
        if resp:
            resp_tokens = resp.split(';')
            baseresp, resp_params = resp_tokens[0], resp_tokens[1:]

            if baseresp == "CONN_SUCCESS":
                logging.info("Connected on %s:%d", self.ip, self.port)
                self.running = True
            elif baseresp == "CONN_FAILURE":
                logging.error("Connection to %s:%d failed (%s)", self.ip,
                              self.port, resp_params[0])
            elif baseresp == "DISCONNECT":
                self.disconnect()
                self.reconnect()
            elif baseresp == "RESP":
                logging.info("Command succeeded.")
                if resp_params:
                    print("Response parameters are: {0}".format('\t'.join(resp_params)))
            elif baseresp == "RESP_SUCCESS":
                logging.info("Command succeeded.")
            elif baseresp == "RESP_FAILURE":
                logging.warning("Command failed.")

    def run_command(self, cmd):
        """
        Send user commands to server and parse output.
        """
        # Check syntax.
        cmd = cmd.upper()
        if self.valid_command(cmd):
            if cmd == "EXIT":
                self.disconnect()
                self.running = False
                return

            self.safe_send(cmd)
            resp = self.safe_read()
            self.handle_output(resp)

    def disconnect(self):
        """
        Discontinue server connection.
        """
        self.safe_send("DISCONNECT")

        if socket:
            self.socket.close()

    def reconnect(self):
        """
        Attempt to reconnect to server.
        """
        wait_time = 2
        while True:
            logging.info("Attempting to reconnect in %d seconds", wait_time)
            time.sleep(wait_time)
            if wait_time < 32:
                wait_time *= 2

            self.connect()
            if self.socket:
                break

    def safe_send(self, data):
        """
        Send a message to server.
        """
        if not self.socket:
            logging.warning("Attempting to send without a connection, "
                            "ignoring...")
            return
        else:
            try:
                logging.info("Sending %s", data)
                data += '\n'
                data = data.encode('ascii')
                self.socket.send(data)
            except ConnectionRefusedError:
                logging.warning("Connection to socket failed.")
                return
            except (ConnectionAbortedError, ConnectionResetError):
                logging.warning("Connection to socket terminated.")
                return
            except OSError:
                return

            # everything succeeded, so return a non-null value
            return True

    def safe_read(self):
        """
        Read data from server.
        """
        if not self.socket:
            logging.warning("Attempting to recv without a connection, "
                            "ignoring...")
            return
        else:
            try:
                data = self.socket.recv(BUFFER_SIZE)
            except socket.timeout:
                logging.warning("Command timed out.")
                return
            except ConnectionRefusedError:
                logging.warning("Connection to socket failed.")
                return
            except (ConnectionAbortedError, ConnectionResetError):
                logging.warning("Connection to socket terminated.")
                return
            except OSError:
                return

            data = data.decode('ascii').strip()
            if not data:
                self.disconnect()
                logging.warning("Connection to socket terminated.")
                self.reconnect()
            else:
                logging.info("Received %s", data)
            return data
