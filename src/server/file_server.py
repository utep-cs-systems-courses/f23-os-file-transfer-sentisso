import socket
import os
from socket_server import SocketServer
from typing import Literal, Dict, TypedDict

# directory of this file
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class TransferState(TypedDict):
    """
    Represents the state of a file transfer.
    Attributes:
        action: 'U' - client is sending (Uploading) a file, 'D' - client is receiving (Downloading) a file
        fname: The name of the file.
        fname_len: The length of the filename (as reported by the client).
        confirmed: Whether the action for the file has been confirmed by the server.
        fsize: The size of the file.
        fpos: The current position in the file.
    """
    action: Literal['U', 'D']
    fname: str
    fname_len: int
    confirmed: bool
    fsize: int
    fsize_buffer: bytearray
    fpos: int
    fd: int | None


class FileServer:
    def __init__(self, socket_server: SocketServer, data_folder: str, byteorder="little"):
        self.__socket_server = socket_server
        self.__data_folder = os.path.abspath(os.path.join(ROOT_DIR, data_folder))
        self.__byteorder = byteorder

        self.__socket_server.on("data", self.__on_data)
        self.__socket_server.on("connect", self.__on_connect)
        self.__socket_server.on("disconnect", self.__on_disconnect)

        # __transfers[port] = state of the file transfer for the client at port
        self.__transfers: Dict[int, TransferState] = {}

    # region File server methods

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
        print("[%d] connected" % (addr[1]))

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
        arr = bytearray(data)
        addr, port = fd.getpeername()

        active_transfer = self.__transfers.get(port, None)
        if active_transfer is None:
            # client has no active transfer
            action = chr(data[0])
            del arr[:1]

            active_transfer = self.__prepare_transfer(port, action)

            if action == 'U':
                print('[%d] -> requesting to upload a file...' % port)
            elif action == 'D':
                print('[%d] -> requesting to download a file...' % port)
            else:
                # user sent an unexpected action, disconnect them
                print('[%d] unexpected action "%s"!' % (port, action))
                return self.disconnect(fd)

        # continue client's transfer...
        if active_transfer['action'] == 'U':
            self.__process_upload(fd, arr)

        elif active_transfer['action'] == 'D':
            self.__process_download(fd, arr)

    # endregion

    # region Transfer processing

    def __process_upload(self, fd: socket.socket, data: bytes):
        if len(data) <= 0:
            return

        buffer = bytearray(data)
        addr, port = fd.getpeername()
        transfer = self.__transfers[port]

        if self.__read_filename(transfer, buffer) > 0:
            return  # the filename is not complete yet

        if self.__read_fsize(transfer, buffer) > 0:
            return  # the fsize is not complete yet

        if not transfer['confirmed']:
            print('[%d] -> file is "%s" with size (%dB)' % (port, transfer['fname'], transfer['fsize']))

            # check the reported file size
            if not 0 < transfer['fsize'] < 2 ** 64:
                self.__send_confirmation(fd, False, "Invalid file size!")
                return self.disconnect(fd)

            # check other stuff...

            # requested file is valid, send a confirmation
            self.__send_confirmation(fd, True)
            transfer['confirmed'] = True

            print("[%d] -> sending file (%dB)..." % (port, transfer['fsize']))

        # read the file from the client
        if self.__read_file(transfer, buffer) > 0:
            return  # the file is not complete yet

        print("[%d] -> file has been received: %s" % (port, self.__get_file_path(transfer)))

        self.__send_confirmation(fd, True)

        # end the transfer
        self.__end_transfer(port)

    def __process_download(self, fd: socket.socket, data: bytes):
        if len(data) <= 0:
            return

        buffer = bytearray(data)
        addr, port = fd.getpeername()
        transfer = self.__transfers[port]

        if self.__read_filename(transfer, buffer) > 0:
            return  # the filename is not complete yet, wait for more data

        # validate the request and send a confirmation
        if not transfer['confirmed']:
            print('[%d] -> file is: %s' % (port, self.__get_file_path(transfer)))

            # check the file existence
            if not os.path.exists(self.__get_file_path(transfer)):
                self.__send_confirmation(fd, False, "File not found!")
                return self.disconnect(fd)

            # check other stuff...

            # requested file is valid, send a confirmation
            self.__send_confirmation(fd, True)
            transfer['confirmed'] = True

        # write the file to the client
        self.__send_file(fd, transfer)

        # end the transfer
        self.__end_transfer(port)

    # endregion

    # region Framing/un-framing

    def __read_filename(self, transfer: TransferState, buffer: bytearray):
        """
        Reads the fname from the socket until the fname is complete.
        :param transfer:
        :param buffer: mutable bytearray containing the received data
        :return: Number of bytes remaining for the fname to be complete.
        """
        if transfer['fname_len'] == 0:
            transfer['fname_len'] = int.from_bytes(buffer[:1], self.__byteorder)
            if transfer['fname_len'] <= 0:
                raise Exception("Invalid filename length %d" % transfer['fname_len'])

            del buffer[:1]

        diff = transfer['fname_len'] - len(transfer['fname'])
        if diff > 0:
            transfer['fname'] += buffer[:diff].decode("utf-8")
            del buffer[:diff]

            diff = transfer['fname_len'] - len(transfer['fname'])

        return diff

    def __read_fsize(self, transfer: TransferState, buffer: bytearray):
        """
        Reads the fsize from the socket until the fsize is complete.
        :param transfer:
        :param buffer: mutable bytearray containing the received data
        :return: Number of bytes remaining for the fsize to be complete.
        """
        diff = 8 - len(transfer['fsize_buffer'])
        if diff > 0:
            transfer['fsize_buffer'] += buffer[:diff]
            del buffer[:diff]

            diff = 8 - len(transfer['fsize_buffer'])

            if diff == 0:
                transfer['fsize'] = int.from_bytes(
                    transfer['fsize_buffer'], self.__byteorder
                )

        return diff

    def __read_file(self, transfer: TransferState, buffer: bytearray):
        """
        Read the file from the socket and write it to the filesystem.
        :param transfer:
        :param buffer: mutable bytearray containing the received data
        :return:
        """
        if transfer['fd'] is None:
            transfer['fd'] = os.open(self.__get_file_path(transfer), os.O_WRONLY | os.O_CREAT | os.O_TRUNC)

        diff = transfer['fsize'] - transfer['fpos']
        if diff > 0:
            transfer['fpos'] += os.write(transfer['fd'], buffer[:diff])
            del buffer[:diff]

            diff = transfer['fsize'] - transfer['fpos']

            if diff == 0:
                os.close(transfer['fd'])
                transfer['fd'] = None

        return diff

    def __send_confirmation(self, fd: socket.socket, ok: bool, error: str = None):
        """
        Send a confirmation message to the client.
        :param fd:
        :param ok: if "OK" or "ERROR"
        :param error: Error message in case of `not ok`.
        :return:
        """
        addr, port = fd.getpeername()
        if not ok and (error is None or not 0 < len(error) < 256):
            raise Exception("Missing or invalid error message for a confirmation!")

        self.__socket_server.send(
            fd,
            int.to_bytes(0 if ok else 1, 1, self.__byteorder)
        )

        msg = "OK" if ok else "ERROR"

        if not ok:
            self.__socket_server.send(
                fd,
                int.to_bytes(len(error), 1, self.__byteorder) + bytes(error.encode("utf-8"))
            )

            msg += ": %s" % error

        print("[%d] <- %s" % (port, msg))

    def __send_file(self, fd: socket.socket, transfer: TransferState):
        """
        Read the requested file from the filesystem and send it to the client.
        :param fd:
        :param transfer:
        :return:
        """
        addr, port = fd.getpeername()
        transfer['fd'] = os.open(self.__get_file_path(transfer), os.O_RDONLY)
        transfer['fsize'] = os.fstat(transfer['fd']).st_size

        # write the size of the file that is about to be sent
        self.__socket_server.send(
            fd,
            int.to_bytes(transfer['fsize'], 8, self.__byteorder)
        )

        print("[%d] <- sending file (%dB)..." % (port, transfer['fsize']))

        # write all the file contents
        while True:
            buffer = os.read(transfer['fd'], 1024)
            if not buffer:
                break

            self.__socket_server.send(fd, buffer)

        print("[%d] file has been sent" % port)

    # endregion

    # region Transfer state management

    def __prepare_transfer(self, port: int, action: str):
        """
        Prepare a file transfer for a client.
        :param port:
        :param action:
        :return: The just created transfer state.
        """
        self.__transfers[port] = {
            'action': action,
            'fname': '', 'fname_len': 0, 'confirmed': False,
            'fsize': 0, 'fsize_buffer': bytearray(0),
            'fpos': 0, 'fd': None
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

    def __get_file_path(self, transfer: TransferState):
        """
        Get the absolute path to the file that is managed by the given transfer state.
        """
        return os.path.abspath(os.path.join(self.__data_folder, transfer['fname']))

    # endregion
