#! /usr/bin/env python3
import signal, sys, os

dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(dir, '..')))

import lib.params as params
from socket_server import SocketServer
from file_server import FileServer

flags = (
    (('-l', '--listenPort'), 'listenPort', 50001),
    (('-c', '--connections'), 'connections', 100),
    (('-?', '--usage'), "usage", False),  # boolean (set if present)
)

param_map = params.parseParams(flags)
if param_map['usage']:
    params.usage()
    sys.exit(0)

socket_server = SocketServer(param_map['listenPort'], param_map['connections'])
file_server = FileServer(socket_server, "../../data/server", "little")


def signal_handler(sig, frame):
    global socket_server
    print('Closing socket server and exitting...')
    socket_server.close()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

file_server.listen()
