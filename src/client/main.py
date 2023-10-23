#! /usr/bin/env python3
import os, sys, signal, re

dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(dir, '..')))

import file_client


def print_usage():
    print("Usage:")
    print("   client.py <file_to_upload> <host:port>")
    print("   client.py <host:port>@<file_to_download>")


def incorrect_usage():
    print_usage()
    sys.exit(1)


action = None
server = None
if len(sys.argv) == 3:
    # if command is to upload
    action = 'U'
    server = sys.argv[2]
    fname = sys.argv[1]

elif len(sys.argv) == 2:
    # if command is to download
    action = 'D'
    params = sys.argv[1].split('@')
    if len(params) != 2:
        incorrect_usage()

    server = params[0]
    fname = params[1]

else:
    incorrect_usage()  # will exit

# try to parse the server address
try:
    server_host, server_port = server.split(":")
    server_port = int(server_port)
except:
    incorrect_usage()

if len(server_host) == 0 or len(fname) == 0 or not 0 < server_port < 65536:
    incorrect_usage()

# run the client
client = file_client.Client(server)
if not client.connect():
    print('[client] could not connect to %s. Exiting...' % server)


def signal_handler(sig, frame):
    global client
    print('Closing socket server and exitting...')
    client.exit(0)


signal.signal(signal.SIGINT, signal_handler)

if action == 'D':
    client.download_file(fname)
elif action == 'U':
    client.upload_file(fname)

client.close()
