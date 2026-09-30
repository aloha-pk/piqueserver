# Copyright (c) Mathias Kaerlev 2011-2012.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

"""
The ByteReader/Bytewriter classes are used to read and write various data types
from and to byte-like objects. This is used e.g. to read the contents of
packets.
"""

cdef extern from "bytes_c.c":
    struct Strm:
        char *buf
        Py_ssize_t off
        Py_ssize_t len
        Py_ssize_t alloc

    Strm *strm_creat()
    void strm_close(Strm *strm)

    # great use of stdint.h. . .
    char  read_byte(void *data)
    short read_short(void *data)
    int   read_int(void *data)

    unsigned char  read_ubyte(void *data)
    unsigned short read_ushort(void *data)
    unsigned int   read_uint(void *data)

    float read_float(void *data)
    char *read_string(void *data)

    void write_buf(Strm *strm, char *data, Py_ssize_t size)
    void write_byte(Strm *strm, char val)
    void write_short(Strm *strm, short val)
    void write_int(Strm *strm, int val)
    void write_float(Strm *strm, float val)
    void write_string(Strm *strm, char *data, Py_ssize_t size)
    void rewind_stream(Strm *strm, Py_ssize_t off)
    bytes get_stream(Strm *strm)
    Py_ssize_t get_stream_size(Strm *strm)
    Py_ssize_t get_stream_pos(Strm *strm)

class NoDataLeft(Exception):
    pass

DEF INT_ERROR = -0xFFFFFFFF >> 1
DEF LONG_LONG_ERROR = -0xFFFFFFFFFFFFFFFF >> 1

cdef class ByteReader:
    """Reads various data types from a bytes-like object"""
    def __init__(self, input_data, Py_ssize_t start = 0, Py_ssize_t size = -1):
        self.input = input_data
        self.data = input_data
        self.data += start
        self.pos = self.data
        if size == -1:
            size = len(input_data) - start
        self.size = size
        self.end = self.data + size
        self.start = start

    cdef char * check_available(self, Py_ssize_t size):
        cdef char * data = self.pos
        if data + size > self.end:
            raise NoDataLeft('not enough data')
        self.pos += size
        return data

    cpdef read(self, Py_ssize_t bytecount = -1):
        """read a number of bytes

        Arguments:
            bytecount (int, optional): The number of bytes to read. If omitted, all bytes available are read

        Returns:
            bytes: ``bytecount`` bytes of data
        """
        cdef Py_ssize_t left = self.dataLeft()
        if bytecount == -1 or bytecount > left:
            bytecount = left
        ret = self.pos[:bytecount]
        self.pos += bytecount
        return ret

    cpdef int readByte(self, bint unsigned = False):
        """read one byte of data as integer

        Arguments:
            unsigned (bool): If true, interpret the byte as unsigned

        Returns:
            int: The value of the byte as int
        """
        cdef char * pos = self.check_available(1)
        if unsigned:
            return read_ubyte(pos)
        else:
            return read_byte(pos)

    cpdef int readShort(self, bint unsigned = False, bint big_endian = True):
        """read two bytes of data as integer

        Arguments:
            unsigned (bool): If true, interpret the bytes as unsigned
            big_endian (bool, optional): If true, interpret the bytes as big endian

        Returns:
            int: The value of the bytes as int
        """
        cdef char * pos = self.check_available(2)
        if unsigned:
            return read_ushort(pos)
        else:
            return read_short(pos)

    cpdef long long readInt(self, bint unsigned = False, bint big_endian = True):
        """read four bytes of data as integer

        Arguments:
            unsigned (bool): If true, interpret the bytes as unsigned
            big_endian (bool, optional): If true, interpret the bytes as big endian

        Returns:
            int: The value of the bytes as int
        """
        cdef char * pos = self.check_available(4)
        if unsigned:
            return read_uint(pos)
        else:
            return read_int(pos)

    cpdef float readFloat(self, bint big_endian = True):
        """read four bytes of data as floating point number

        Arguments:
            big_endian (bool, optional): If true, interpret the bytes as big endian

        Returns:
            float: The value of the bytes as float
        """
        cdef char * pos = self.check_available(4)
        return read_float(pos)

    cpdef bytes readString(self, Py_ssize_t size = -1):
        """read a string

        Arguments:
            size (int): If set, read ``size`` bytes, else read all bytes available

        Returns:
            bytes: The value of the bytes
        """
        value = self.pos
        if size == -1:
            size = len(value) + 1
        if size > self.end - self.pos:
            size = self.end - self.pos
            value = value[:size]
        self.pos += size
        return bytes(value)

    cpdef ByteReader readReader(self, Py_ssize_t size = -1):
        cdef Py_ssize_t left = self.dataLeft()
        if size == -1 or size > left:
            size = left
        cdef ByteReader reader = ByteReader(self.input,
            (self.pos - self.data) + self.start, size)
        self.pos += size
        return reader

    cpdef Py_ssize_t tell(self):
        """get the current position in the buffer

        Returns:
            int: The current position in bytes"""
        return self.pos - self.data

    cpdef Py_ssize_t dataLeft(self):
        """get the number of bytes left in the buffer

        Returns:
            int: The number of bytes left"""
        return self.end - self.pos

    cpdef seek(self, Py_ssize_t pos):
        """move to a position in the buffer

        Arguments:
            pos (int): position to seek to
        """
        self.pos = self.data + pos
        if self.pos > self.end:
            self.pos = self.end
        if self.pos < self.data:
            self.pos = self.data

    cdef void _skip(self, Py_ssize_t bytecount):
        self.pos += bytecount
        if self.pos > self.end:
            self.pos = self.end
        if self.pos < self.data:
            self.pos = self.data

    cpdef skipBytes(self, Py_ssize_t bytecount):
        """move the position ``bytecount`` bytes ahead

        Arguments:
            bytecount: number of bytes to move ahead
        """
        self._skip(bytecount)

    cpdef rewind(self, Py_ssize_t off):
        """move the position ``bytecount`` bytes back

        Arguments:
            bytecount: number of bytes to move back
        """
        self._skip(-off)

    def __len__(self):
        return self.size

    def __bytes__(self):
        return self.data[:self.size]

cdef class ByteWriter:
    def __init__(self):
        self.stream = strm_creat()

    cdef void writeSize(self, char *data, Py_ssize_t size):
        write_buf(self.stream, data, size)

    cpdef write(self, data):
        write_buf(self.stream, data, len(data))

    cpdef writeByte(self, int value, bint unsigned = False):
        write_byte(self.stream, value)

    cpdef writeShort(self, int value, bint unsigned = False,
                     bint big_endian = True):
        write_short(self.stream, value)

    cpdef writeInt(self, long long value, bint unsigned = False,
                   bint big_endian = True):
        write_int(self.stream, value)

    cpdef writeFloat(self, float value, bint big_endian = True):
        write_float(self.stream, value)

    cpdef writeStringSize(self, char *value, Py_ssize_t size):
        write_string(self.stream, value, size)

    cpdef writeString(self, value, Py_ssize_t size = -1):
        write_string(self.stream, value, len(value))
        if size != -1:
            self.pad(size - (len(value) + 1))

    cpdef pad(self, Py_ssize_t bytecount):
        cdef Py_ssize_t i
        for i in range(bytecount):
            write_byte(self.stream, 0)

    cpdef rewind(self, Py_ssize_t bytecount):
        rewind_stream(self.stream, bytecount)

    cpdef size_t tell(self):
        return get_stream_pos(self.stream)

    def __bytes__(self):
        return get_stream(self.stream)

    def __dealloc__(self):
        strm_close(self.stream)

    def __len__(self):
        return get_stream_size(self.stream)
