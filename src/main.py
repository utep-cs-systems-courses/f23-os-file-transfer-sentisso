#! /usr/bin/env python3
import socket
import sys, os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(ROOT_DIR, '..')))  # for params

import lib.params as params
from server import Server

flags = (
    (('-l', '--listenPort'), 'listenPort', 50001),
    (('-c', '--connections'), 'connections', 100),
    (('-?', '--usage'), "usage", False),  # boolean (set if present)
)

param_map = params.parseParams(flags)

if param_map['usage']:
    params.usage()
    sys.exit(0)

server = Server(param_map['listenPort'], param_map['connections'])


def on_connect(addr):
    addr, port = addr
    print("[%d] connected" % port)


def on_disconnect(addr):
    addr, port = addr
    print("[%d] disconnected" % port)


def on_data(fd: socket.socket, data: bytes):
    data = data.decode()
    addr, port = fd.getpeername()

    print("[%d] -> '%s'" % (port, data))

    echo = "Echoing %s" % data
    server.send(fd, echo.encode())
    print("[%d] <- '%s'" % (port, echo))


server.on("data", on_data)
server.on("connect", on_connect)
server.on("disconnect", on_disconnect)
server.listen()
