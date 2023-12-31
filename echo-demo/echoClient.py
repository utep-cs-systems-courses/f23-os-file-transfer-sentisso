#! /usr/bin/env python3

# Echo client program
import socket, sys, re, os, time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(ROOT_DIR, '..')))  # for params

import lib.params as params

flags = (
    (('-s', '--server'), 'server', "127.0.0.1:50001"),
    (('-?', '--usage'), "usage", False),  # boolean (set if present)
)

param_map = params.parseParams(flags)

server, usage = param_map["server"], param_map["usage"]

if usage:
    params.usage()

try:
    serverHost, serverPort = re.split(":", server)
    serverPort = int(serverPort)
except:
    print("Can't parse server:port from '%s'" % server)
    sys.exit(1)

s = None
for res in socket.getaddrinfo(serverHost, serverPort, socket.AF_UNSPEC, socket.SOCK_STREAM):
    af, socktype, proto, canonname, sa = res
    try:
        print("creating sock: af=%d, type=%d, proto=%d" % (af, socktype, proto))
        s = socket.socket(af, socktype, proto)
    except socket.error as msg:
        print(" error: %s" % msg)
        s = None
        continue
    try:
        print(" attempting to connect to %s" % repr(sa))
        s.connect(sa)
    except socket.error as msg:
        print(" error: %s" % msg)
        s.close()
        s = None
        continue
    break

if s is None:
    print('could not open socket')
    sys.exit(1)

for i in range(50):
    outMessage = "Hello world!".encode()
    while len(outMessage):
        print("[server] <- '%s'" % outMessage.decode())
        bytesSent = os.write(s.fileno(), outMessage)
        outMessage = outMessage[bytesSent:]

    data = os.read(s.fileno(), 1024).decode()
    print("[server] -> '%s'" % data)

    time.sleep(2)

s.shutdown(socket.SHUT_WR)  # no more output

s.close()
