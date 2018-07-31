#!/usr/bin/env python

from json import loads
import logging
import re
import socket
from select import select

import time
from threading import Thread
from pkg_resources import resource_string

BUFFER_SIZE = 100

# Set the format for log messages (warnings, errors, etc.)
LOG_FORMAT = "[%(levelname)s] [%(msecs)d] [%(threadName)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT)
logging.getLogger().setLevel(logging.INFO)


class Node:

    def __init__(self, name, type_):
        self.name = name
        self.type = type_

        self.ip = None
        self.port = None

        self.socket = None

        # Is the connection active?
        self.running = False

        # Are we waiting for a response to a command we sent to the server?
        # (This momentarily deactivates the watcher so that it doesn't eat
        # responses.)
        self.waiting = False

        # The following lines do the same thing as load(open('protocol.json'))
        # but also work when this file is being called as part of a submodule,
        # which it is. For more details, see:
        # https://stackoverflow.com/questions/6028000/how-to-read-a-static-file-from-inside-a-python-package
        resource_package = __name__
        resource_path = '/'.join(('protocol.json',))
        protocol = resource_string(resource_package, resource_path)

        # Load the command syntax file.
        self.protocol = loads(protocol)

    def connect(self):
        """
        Attempt to establish a connection with server.
        """
        self.socket = None

        # Make sure we're connecting to something.
        if not (self.ip and self.port):
            if not self.ip:
                logging.error("IP address not set.")
            if not self.port:
                logging.error("Port not set.")
            return

        # Initialize socket.
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
            # Perform server handshake.
            logging.info("Found socket on %s:%d", self.ip, self.port)

            logging.info("Beginning handshake")
            data = self.safe_read()
            if data == 'WHOIS':
                resp = "{0};{1}\n".format(self.name, self.type)
                self.safe_send(resp)

            data = self.safe_read()
            success, _ = self.handle_output(data)

            if success:
                # We're connected. Start a separate thread to listen for
                # incoming input from the server (like disconnect
                # notifications.)
                watcher = Thread(target=self.watch)
                watcher.start()
        else:
            logging.error("No socket found.")
            return

    def watch(self):
        """
        Watch for incoming input from server.
        """
        while self.running:
            time.sleep(0.1)
            is_watching = (self.socket and not self.waiting
                           and self.socket.fileno() >= 0)
            if is_watching:
                has_data, _, _ = select([self.socket], [], [], 1)
                if has_data:
                    data = self.safe_read()
                    self.handle_output(data)

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
            if not (spec["min_args"] <= len(args) < spec["max_args"]):
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
                return (True, tuple())
            elif baseresp == "CONN_FAILURE":
                logging.error("Connection to %s:%d failed (%s)", self.ip,
                              self.port, resp_params[0])
                return (False, tuple())
            elif baseresp == "DISCONNECT":
                self.disconnect()
                self.running = False
                self.reconnect()
                return (False, tuple())
            elif baseresp == "RESP":
                logging.info("Command succeeded.")
                if resp_params:
                    logging.info("Response parameters are: {0}".format(
                                 '\t'.join(resp_params)))
                return (True, tuple(resp_params))
            elif baseresp == "RESP_SUCCESS":
                logging.info("Command succeeded.")
                return (True, tuple())
            elif baseresp == "RESP_FAILURE":
                logging.warning("Command failed.")
                return (False, tuple())

    def run_command(self, cmd, *args):
        """
        Send user commands to server and parse output.
        """
        data = ';'.join([cmd] + list(args))
        # Check syntax.
        data = data.upper()
        print(data)
        if self.valid_command(data):
            self.waiting = True
            self.safe_send(data)
            resp = self.safe_read()
            self.waiting = False
            success, params = self.handle_output(resp)

            return (success, params)
        return (False, tuple())

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
            if wait_time < 512:
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
