import socket, select
from typing import List


class SocketServer:
    """
    A wrapper class around a socket server. Handles read/write events and new connections.
    """

    def __init__(self, port, max_conns, read_buffer_len=1024):
        self.__read_buffer_len = read_buffer_len
        self.__max_conns = max_conns
        self.__port = port

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__socket.bind(('', self.__port))

        self.__readfds: List[socket.socket] = [self.__socket]
        self.__is_listening = False

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
            print('[server] warning: already listening!')
            return

        self.__socket.listen(self.__max_conns)
        self.__is_listening = True

        print('[server] listening on port %d...' % self.__port)

        if self.__events['data'] is None:
            print('[server] warning: no data event handler set!')

        while True:
            rlist, wlist, xlist = select.select(
                self.__readfds, [], []
            )
            self.__handle_select(rlist, wlist, xlist)

    def send(self, fd: socket.socket, data: bytes):
        """
        Send all the given data to a client.
        :param fd: The client socket to send data to.
        :param data: The data to send.
        :return:
        """
        return fd.sendall(data)

    def disconnect(self, fd: socket.socket):
        """
        Disconnect a client.
        :param fd: The client socket to disconnect.
        :return:
        """
        self.__readfds.remove(fd)
        fd.close()

    def close(self):
        """
        Close the server socket.
        :return:
        """
        self.__socket.shutdown(socket.SHUT_RDWR)
        self.__socket.close()

    def on(self, event, callback):
        """
        Set an event callback. Available events are:
        - connect - called when a new client connects ((addr, port))
        - disconnect - called when a client disconnects ((addr, port))
        - data - called when a client sends data (fd, data), receives at most `read_buffer_len` bytes
        :param event:
        :param callback:
        :return:
        """
        self.__events[event] = callback

        return self

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

        if self.__events['connect']:
            self.__events['connect'](addr)

    def __handle_select_read(self, fd: socket.socket):
        """
        Handle a read event.
        :param fd: The file descriptor to read from.
        :return:
        """
        addr, port = fd.getpeername()

        data = fd.recv(self.__read_buffer_len)

        if len(data) == 0:
            self.__readfds.remove(fd)
            fd.close()
            if self.__events['disconnect']:
                self.__events['disconnect']((addr, port))
            return

        if self.__events['data']:
            self.__events['data'](fd, data)
