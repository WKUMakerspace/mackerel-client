#!/usr/bin/env python

import argparse
from MackerelClient import MackerelClient


def __main__():
    parser = argparse.ArgumentParser(description="Run the Mackerel client program.")
    parser.add_argument("name", metavar="CLIENT_NAME", default="client",
                        help="Client identifier.")
    parser.add_argument("type", metavar="CLIENT_TYPE", default="kiosk",
                        help="Client type (one of 'kiosk', 'tool', 'admin')")
    parser.add_argument("ip", metavar="SERVER_IP", default="127.0.0.1", nargs="?",
                        help="Server's IP address, defaults to 127.0.0.1")
    parser.add_argument('port', metavar='SERVER_PORT',
                        default=4400, type=int, nargs="?",
                        help="Server's port, defaults to 4400")

    args = parser.parse_args()
    if args.type not in ("kiosk", "tool", "admin"):
        raise ValueError("type must be one of 'kiosk', 'tool', 'admin'")

    client = MackerelClient(args.name, args.type)
    client.ip = args.ip
    client.port = args.port
    client.connect()
    client.run()


if __name__ == '__main__':
    __main__()
