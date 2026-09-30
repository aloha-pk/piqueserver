/* rough port of pvx/pyspades/bytewriterclass.c to work with cython garbage */
#include "Python.h"
#include <stdint.h>
#include <stdlib.h>

struct Strm {
	char *buf;
	Py_ssize_t off;
	Py_ssize_t len;
	Py_ssize_t alloc;
};

static struct Strm *strm_creat(void)
{
	struct Strm *strm = PyMem_Malloc(sizeof(struct Strm));
	if (strm == NULL)
		abort();

	strm->buf = PyMem_Malloc(1024);
	if (strm->buf == NULL)
		abort();

	strm->off = 0;
	strm->len = 0;
	strm->alloc = 1024;

	return strm;
}

static void strm_close(struct Strm *strm)
{
	PyMem_Free(strm->buf);
	PyMem_Free(strm);
}

static void stretch(struct Strm *strm, Py_ssize_t len)
{
	if (strm->off + len > strm->alloc) {
		size_t newalloc = strm->off+len;
		char *newbuf = PyMem_Realloc(strm->buf, newalloc);

		if (newbuf == NULL)
			abort();

		strm->buf = newbuf;
		strm->alloc = newalloc;
	}
}

static Py_ssize_t get_stream_pos(struct Strm *strm)
{
	return strm->off;
}

static Py_ssize_t get_stream_size(struct Strm *strm)
{
	return strm->len;
}

static PyObject *get_stream(struct Strm *strm) {
	return PyBytes_FromStringAndSize(strm->buf, strm->len);
}

static void rewind_stream(struct Strm *strm, Py_ssize_t off)
{
	strm->off -= off;

	if (strm->off > strm->len)
		strm->off = strm->len;

	if (strm->off < 0)
		strm->off = 0;
}

static void write_buf(struct Strm *strm, void *buf, Py_ssize_t len)
{
	stretch(strm, len);

	memcpy(strm->buf+strm->off, buf, len);
	strm->off += len;

	if (strm->off > strm->len)
		strm->len = strm->off;
}

static void write_string(struct Strm *strm, void *buf, Py_ssize_t len)
{
	write_buf(strm, buf, len);
	write_buf(strm, "", 1);
}

static void write_byte(struct Strm *strm, int8_t val)
{
	write_buf(strm, &val, sizeof(val));
}

static void write_short(struct Strm *strm, int16_t val)
{
	write_buf(strm, &val, sizeof(val));
}

static void write_int(struct Strm *strm, int32_t val)
{
	write_buf(strm, &val, sizeof(val));
}

static void write_float(struct Strm *strm, float val)
{
	write_buf(strm, &val, sizeof(val));
}

static int8_t read_byte(void *data)
{
	return *(int8_t *)data;
}

static int16_t read_short(void *data)
{
	return *(int16_t *)data;
}

static int32_t read_int(void *data)
{
	return *(int32_t *)data;
}

static uint8_t read_ubyte(void *data)
{
	return *(uint8_t *)data;
}

static uint16_t read_ushort(void *data)
{
	return *(uint16_t *)data;
}

static uint32_t read_uint(void *data)
{
	return *(uint32_t *)data;
}

static float read_float(void *data)
{
	return *(float *)data;
}
