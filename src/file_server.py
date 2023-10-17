import socket
from socket_server import SocketServer
from typing import List, Literal, Dict, TypedDict


class TransferState(TypedDict):
    """
    Represents the state of a file transfer.
    Attributes:
        action: 'W' - client is sending (Writing) a file, 'R' - client is receiving (Reading) a file
        fname: The name of the file.
        fsize: The size of the file.
        fpos: The current position in the file.
    """
    action: Literal['W', 'R']
    fname: str
    fname_len: int
    fsize: int
    fpos: int


class FileServer:
    def __init__(self, socket_server: SocketServer):
        self.__socket_server = socket_server

        self.__socket_server.on("data", self.__on_data)
        self.__socket_server.on("connect", self.__on_connect)
        self.__socket_server.on("disconnect", self.__on_disconnect)

        # __transfers[port] = state of the file transfer for the client at port
        self.__transfers: Dict[int, TransferState] = {}

    # region Public file server methods

    def listen(self):
        """
        Start listening for new connections on the underlying socket server and process file transfers for
        connected clients.
        :return:
        """
        self.__socket_server.listen()

    def disconnect(self, fd: socket.socket):
        """
        Disconnect a client.
        :param fd: The client socket to disconnect.
        :return:
        """
        addr, port = fd.getpeername()
        print("[%d] disconnecting by server..." % port)
        self.__socket_server.disconnect(fd)

    # endregion

    # region Socket event handlers

    def __on_connect(self, addr):
        addr, port = addr
        print("[%d] connected" % port)

    def __on_disconnect(self, addr):
        """
        When user is disconnected, end their current file transfer (if any).
        :param addr:
        :return:
        """
        addr, port = addr
        self.__end_transfer(port)
        print("[%d] disconnected" % port)

    def __on_data(self, fd: socket.socket, data: bytes):
        addr, port = fd.getpeername()

        active_transfer = self.__transfers.get(port, None)
        if active_transfer is None:
            # client has no active transfer
            action = chr(data[0])
            active_transfer = self.__start_transfer(port, action)

            if action == 'W':
                print('[%d] client wants to write a file' % port)
                data = data[1:]
            elif action == 'R':
                print('[%d] client is requesting a file' % port)
                data = data[1:]
            else:
                # user sent an unexpected action, disconnect them
                print('[%d] unexpected action "%s"!' % (port, action))
                return self.disconnect(fd)

        # continue client's transfer...
        if active_transfer['action'] == 'W':
            self.__process_write(fd, data)

        elif active_transfer['action'] == 'R':
            self.__process_read(fd, data)

    # endregions

    # region Transfer state management

    def __start_transfer(self, port: int, action: str):
        """
        Start a file transfer for a client.
        :param port:
        :param action:
        :return: The just created transfer state.
        """
        self.__transfers[port] = {
            'action': action,
            'fname': '', 'fname_len': 0,
            'fsize': 0, 'fpos': 0
        }
        return self.__transfers[port]

    def __end_transfer(self, port: int):
        """
        End a file transfer for a client.
        :param port:
        :return:
        """
        if port not in self.__transfers:
            return

        # TODO: close opened files etc.
        del self.__transfers[port]

    # endregion

    # region Transfer processing

    def __process_write(self, fd: socket.socket, data: bytes):
        pass

    def __process_read(self, fd: socket.socket, data: bytes):
        pass

    # endregion
