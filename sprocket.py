#!/usr/bin/env python

import asyncio
import socket
import argparse

BUFFER_SIZE = 20


async def socket_out(s):
    input_ = await input()
    s.send(input_)


async def socket_in(s):
    output = await s.recv(BUFFER_SIZE)
    print(output)


def __main__():
    parser = argparse.ArgumentParser(description="Tcp client for Liam")

    parser.add_argument("ip", nargs='?', type=str, default='127.0.0.1')
    parser.add_argument("port", nargs='?', type=int, default=4000)

    args = parser.parse_args()

    TCP_IP = args.ip
    TCP_PORT = args.port

    s = socket.socket()
    s.connect((TCP_IP, TCP_PORT))

    ioloop = asyncio.get_event_loop()
    tasks = [ioloop.create_task(socket_in(s)),
             ioloop.create_task(socket_out(s))]

    ioloop.run_until_complete(asyncio.wait(tasks))


if __name__ == "__main__":
    __main__()
