#!/usr/bin/env python

import asyncio
import argparse
from time import sleep

BUFFER_SIZE = 32

class Sprocket:

    def __init__(self, nid, ntype):
        self.id = nid
        self.type = ntype
        self.reader = None
        self.writer = None

    def run(self):
        if self.conn:
            try:
                print("Starting event loop")
                loop = asyncio.get_event_loop()
                asyncio.async(self.socket_in())
                asyncio.async(self.socket_out())

                loop.run_forever()
            finally:
                loop.close()

    def try_reconnect(self):
        print("Connection lost.")
        t = 1
        while not self.conn and t < 1024:
            t *= 2
            print("Reconnecting in {0} seconds...".format(t))
            sleep(t)
            self.conn = self.connect()
        if not self.conn:
            print("Connection failed.")
            exit(1)

    @asyncio.coroutine
    def socket_out(self):
        input_ = input('> ')
        self.conn.sendall(input_.encode('utf-8'))
        sleep(0.1)

    @asyncio.coroutine
    def socket_in(self):
        def make_reply(cmd):
            print(cmd)
            if cmd == 'HELLO':
                return 'HELLO'
            elif cmd == 'WHOIS':
                return '{0};{1}'.format(self.id, self.type)
            elif cmd == 'CONN_SUCCESS':
                print("We are connected")
                pass
            elif cmd == 'DISCONNECT':
                self.conn.close()
                self.try_reconnect()
            else:
                return

        print("Getting output")
        output = self.conn.recv(BUFFER_SIZE).decode('utf-8').strip()
        print('Received', output)

        reply = make_reply(output)
        print(repr(reply))
        if reply:
            print('Sending', reply)
            self.conn.send(reply.encode('utf-8'))

        sleep(0.1)


def __main__():
    parser = argparse.ArgumentParser(description="TCP client for Liam")

    parser.add_argument("id", type=str)
    parser.add_argument("type", type=str)
    parser.add_argument("ip", nargs='?', type=str, default='161.6.145.51')
    parser.add_argument("port", nargs='?', type=int, default=4400)

    args = parser.parse_args()

    spr = Sprocket(args.id, args.type)
    spr.connect(args.ip, args.port)
    spr.run()


if __name__ == "__main__":
    __main__()
