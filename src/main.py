#! /usr/bin/env python3
import socket
import sys, os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(ROOT_DIR, '..')))  # for params

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
file_server = FileServer(socket_server)
file_server.listen()
