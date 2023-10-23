#! /usr/bin/env python3

# Echo client program
import socket, sys, re, os

import helpers

READ_BUFFER_LEN = 1024

# directory of this file
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class Client:
    def __init__(self, addr: str, byteorder="little"):
        self.__byteorder = byteorder
        # self.__data_folder = os.path.abspath(os.path.join(ROOT_DIR, data_folder))
        self.__addr = addr
        self.__socket = None

    # region Public methods

    def connect(self) -> bool:
        try:
            serverHost, serverPort = re.split(":", self.__addr)
            serverPort = int(serverPort)
        except:
            print("Can't parse server:port from '%s'" % self.__addr)
            sys.exit(1)

        for res in socket.getaddrinfo(serverHost, serverPort, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                print("[client] creating socket: af=%d, type=%d, proto=%d" % (af, socktype, proto))
                self.__socket = socket.socket(af, socktype, proto)
            except socket.error as msg:
                print("[client] error creating socket: %s" % msg)
                self.__socket = None
                continue

            try:
                print("[client] attempting to connect to %s" % repr(sa))
                self.__socket.connect(sa)
            except socket.error as msg:
                print("[client] error connecting: %s" % msg)
                self.__socket.close()
                self.__socket = None
                continue

            break

        if self.__socket is None:
            return False

        return True

    def download_file(self, fname: str):
        print('[client] requesting to download "%s"...' % fname)

        self.__send("D".encode())
        self.__write_fname(fname)

        buffer = self.__read()

        confirmation = self.__read_confirmation(buffer)

        if confirmation == 1:
            print("[server] -> ERROR: %s" % buffer.decode())
            exit(1)

        elif confirmation == 0:
            print("[server] -> OK")

            fsize = self.__read_fsize(buffer)
            print("[server] -> sending file (%dB)..." % fsize)

            self.__read_file(buffer, fname, fsize)
            print('[client] file has been downloaded: %s' % self.__get_file_path(fname))

        else:
            print("[server] -> ERROR: unknown confirmation code: %d" % confirmation)
            self.exit(1)

    def upload_file(self, fname: str):
        print('[client] requesting to upload "%s"...' % fname)
        if not self.__validate_file(fname):
            print('ERROR: file "%s" does not exist' % fname)
            self.exit(1)

        self.__send("U".encode())
        self.__write_fname(fname)

        fd = os.open(self.__get_file_path(fname), os.O_RDONLY)
        fsize = self.__write_fsize(fd)

        buffer = self.__read()

        confirmation = self.__read_confirmation(buffer)

        if confirmation == 1:
            print("[server] -> ERROR: %s" % buffer.decode())
            self.exit(1)

        elif confirmation == 0:
            print("[server] -> OK")
            print("[server] <- sending file (%dB)..." % fsize)
            self.__write_file(fd)

            buffer = self.__read()
            confirmation = self.__read_confirmation(buffer)

            if confirmation == 1:
                print("[server] -> ERROR: %s" % buffer.decode())
                self.exit(1)
            elif confirmation == 0:
                print("[server] -> OK")
                print('[client] file has been uploaded')


        else:
            print("[server] -> ERROR: unknown confirmation code: %d" % confirmation)
            self.exit(1)

    def close(self):
        self.__socket.shutdown(socket.SHUT_WR)  # no more output
        self.__socket.close()

    def exit(self, status=0):
        self.close()
        sys.exit(status)

    # endregion

    def __read_confirmation(self, buffer: bytearray):
        """
        Read the confirmation code from the buffer.
        :param buffer:
        :return:
        """
        return int.from_bytes(
            helpers.read_buffer(buffer, 1),
            self.__byteorder
        )

    def __read_fsize(self, buffer: bytearray):
        """
        Read the file size from the buffer.
        Will request more data from the socket if the fsize is not complete
        :param buffer:
        :return:
        """
        fsize = helpers.read_buffer(buffer, 8)

        diff = 8 - len(fsize)
        while diff > 0:
            buffer += self.__read()
            fsize += helpers.read_buffer(buffer, diff)
            diff = 8 - len(fsize)

        return int.from_bytes(fsize, self.__byteorder)

    def __read_file(self, buffer: bytearray, fname: str, fsize: int):
        """
        Read the file from the buffer and write it to the given file name.
        Will request more data from the socket if the file is not complete
        :param buffer:
        :param fname:
        :param fsize:
        :return:
        """
        out_fd = os.open(self.__get_file_path(fname), os.O_WRONLY | os.O_CREAT | os.O_TRUNC)

        diff = fsize
        diff -= self.__write_buffer_to_file(buffer, out_fd)

        while diff > 0:
            # we do not have to store the data to a buffer for future use, like `buffer += read()`,
            # since the EOF will be the end of the socket stream itself
            diff -= self.__write_buffer_to_file(self.__read(), out_fd)

        os.close(out_fd)

    def __write_fname(self, fname: str):
        """
        Write the file name to the socket (with its length).
        :param fname:
        :return:
        """
        self.__send(
            int.to_bytes(len(fname), 1, self.__byteorder) +
            fname.encode()
        )

    def __write_fsize(self, fd: int):
        """
        Write the file size to the socket.
        :param fd:
        :return:
        """
        fsize = os.fstat(fd).st_size
        self.__send(
            int.to_bytes(fsize, 8, self.__byteorder)
        )
        return fsize

    def __write_file(self, fd: int, close_fd=True):
        """
        Write the file to the socket.
        :param fd:
        :return:
        """
        while True:
            buffer = os.read(fd, READ_BUFFER_LEN)
            if not buffer:
                break

            self.__send(buffer)

        if close_fd:
            os.close(fd)

    # region Helper methods

    def __send(self, data: bytes, debug=False):
        if debug:
            print('[server] <- "%s" (%s)' % (data.decode(), data))

        self.__socket.sendall(data)

    def __read(self, len=READ_BUFFER_LEN):
        return bytearray(os.read(self.__socket.fileno(), len))

    def __write_buffer_to_file(self, buffer: bytearray, fd: int):
        """
        Read the whole buffer and write it to the given fd.
        :param buffer:
        :param fd:
        :return: Number of bytes that were written (always len(buffer)).
        """
        wrote = len(buffer)
        os.write(fd, helpers.read_buffer(buffer, wrote))
        return wrote

    def __get_file_path(self, fname: str):
        """
        Get the absolute path to the given fname in the data folder.
        """
        # return os.path.abspath(os.path.join(self.__data_folder, fname))
        return fname

    def __validate_file(self, fname: str):
        """
        Check if the given fname is a valid file.
        """
        return os.path.isfile(self.__get_file_path(fname))

    # endregion
