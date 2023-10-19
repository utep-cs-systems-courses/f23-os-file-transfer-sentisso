def read_buffer(buffer: bytearray, len: int):
    """
    Read `len` bytes from the buffer and in-place delete the read bytes from the buffer.
    :param buffer: Mutable bytearray.
    :param len:
    :return: At most `len` long bytearray read from the given buffer.
    """
    out = buffer[:len]
    del buffer[:len]
    return out
