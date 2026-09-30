cdef extern from "bytes_c.c":
    struct Strm:
        char *buf
        Py_ssize_t off
        Py_ssize_t len
        Py_ssize_t alloc


cdef class ByteReader:
    cdef char * data
    cdef char * pos
    cdef char * end
    cdef int start, size
    cdef object input

    cdef char * check_available(self, Py_ssize_t size)
    cpdef read(self, Py_ssize_t bytecount = ?)
    cpdef int readByte(self, bint unsigned = ?)
    cpdef int readShort(self, bint unsigned = ?, bint big_endian = ?)
    cpdef long long readInt(self, bint unsigned = ?, bint big_endian = ?)
    cpdef float readFloat(self, bint big_endian = ?)
    cpdef bytes readString(self, Py_ssize_t size = ?)
    cpdef ByteReader readReader(self, Py_ssize_t size = ?)
    cpdef Py_ssize_t dataLeft(self)
    cdef void _skip(self, Py_ssize_t bytecount)
    cpdef skipBytes(self, Py_ssize_t bytecount)
    cpdef rewind(self, Py_ssize_t off)
    cpdef seek(self, Py_ssize_t pos)
    cpdef Py_ssize_t tell(self)

cdef class ByteWriter:
    cdef Strm *stream

    cdef void writeSize(self, char * data, Py_ssize_t size)
    cpdef write(self, data)
    cpdef writeByte(self, int value, bint unsigned = ?)
    cpdef writeShort(self, int value, bint unsigned = ?,
                     bint big_endian = ?)
    cpdef writeInt(self, long long value, bint unsigned = ?,
                   bint big_endian = ?)
    cpdef writeFloat(self, float value, bint big_endian = ?)
    cpdef writeStringSize(self, char * value, Py_ssize_t size)
    cpdef writeString(self, value, Py_ssize_t size = ?)
    cpdef pad(self, Py_ssize_t bytecount)
    cpdef rewind(self, Py_ssize_t bytecount)
    cpdef size_t tell(self)
