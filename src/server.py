import socket, select, os, sys
from typing import List

READ_BUFFER_LEN = 1024


class Server:
    def __init__(self, port, max_conns):
        self.__max_conns = max_conns
        self.__port = port

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.bind(('', self.__port))

        self.__readfds: List[socket.socket] = [self.__socket]
        self.__is_listening = False

        # dictionary [port] = state of the transfer - can be None, 'sending', or 'receiving'
        self.__transfers = {}

        self.__events = {
            'connect': None,
            'disconnect': None,
            'data': None
        }

    def listen(self):
        """
        Start listening for new connections and handle read/write events.
        :return:
        """
        if self.__is_listening:
            raise Exception("Server is already listening")

        self.__socket.listen(self.__max_conns)
        self.__is_listening = True

        print('[server] listening on port %d...' % self.__port)

        if self.__events['data'] is None:
            raise Exception("No data callback set!")

        while True:
            rlist, wlist, xlist = select.select(
                self.__readfds, [], []
            )
            self.__handle_select(rlist, wlist, xlist)

    def send(self, fd: socket.socket, data: bytes):
        """
        Send data to a client.
        :param fd: The client socket to send data to.
        :param data: The data to send.
        :return:
        """
        while len(data):
            bytes_sent = fd.send(data)
            data = data[bytes_sent:]

    def on(self, event, callback):
        self.__events[event] = callback

    def __handle_select(self, rlist, wlist, xlist):
        """
        Handle the select call.
        :param rlist:
        :param wlist:
        :param xlist:
        :return:
        """
        for fd in rlist:
            # if the fd is the server socket, accept a new connection
            if fd is self.__socket:
                self.__handle_select_new_conn()
            else:
                self.__handle_select_read(fd)

    def __handle_select_new_conn(self):
        """
        Handle a new connection.
        :return:
        """
        conn, addr = self.__socket.accept()
        self.__readfds.append(conn)

        print("[%d] Connected!" % (addr[1]))

        if self.__events['connect']:
            self.__events['connect'](addr)

    def __handle_select_read(self, fd: socket.socket):
        """
        Handle a read event.
        :param fd: The file descriptor to read from.
        :return:
        """
        addr, port = fd.getpeername()

        data = fd.recv(READ_BUFFER_LEN)

        if len(data) == 0:
            print("[%d] Zero length read, terminating..." % (port))
            self.__readfds.remove(fd)
            fd.close()

            if self.__events['disconnect']:
                self.__events['disconnect']((addr, port))

            return

        if self.__events['data']:
            self.__events['data'](fd, data)

        # sendMsg = ("Echoing %s" % data).encode()
        # print("[%d] -> '%s'" % (port, data))
        # print("[%d] <- '%s'" % (port, sendMsg.decode()))
        # while len(sendMsg):
        #     bytesSent = fd.send(sendMsg)
        #     sendMsg = sendMsg[bytesSent:]
