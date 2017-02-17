import struct


class Type:
    T_END = 0
    T_INT = 1
    T_STR = 2
    T_COORD = 3
    T_UINT8 = 4
    T_UINT16 = 5
    T_COLOR = 6
    T_TTOL = 8
    T_INT8 = 9
    T_INT16 = 10
    T_NIL = 12
    T_UID = 13
    T_BYTES = 14
    T_FLOAT32 = 15
    T_FLOAT64 = 16


class Coord:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Color:
    def __init__(self, r, g, b, a):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


class MessageBuf:
    def __init__(self, buf=bytearray()):
        self._buf = bytearray(buf)
        self.pos = 0

    @property
    def buf(self):
        return self._buf

    # NOTE: Auth server uses BE, game server uses LE
    def __end(self, be):
        return '>' if be else '<'

    def add_string(self, s, enc='utf-8'):
        self._buf.extend(s.encode(enc))
        self._buf.append(0)
        self.pos = len(self._buf)

    def add_bytes(self, b):
        self._buf.extend(b)
        self.pos = len(self._buf)

    def add_uint8(self, val):
        self._buf.append(val)
        self.pos = len(self._buf)

    def add_int16(self, val, be=False):
        self._buf.extend(struct.pack(self.__end(be) + 'h', val))
        self.pos = len(self._buf)

    def add_uint16(self, val, be=False):
        self._buf.extend(struct.pack(self.__end(be) + 'H', val))
        self.pos = len(self._buf)

    def add_int32(self, val, be=False):
        self._buf.extend(struct.pack(self.__end(be) + 'i', val))
        self.pos = len(self._buf)

    def add_int64(self, val, be=False):
        self._buf.extend(struct.pack(self.__end(be) + 'q', val))
        self.pos = len(self._buf)

    def add_uint32(self, val, be=False):
        self._buf.extend(struct.pack(self.__end(be) + 'I', val))
        self.pos = len(self._buf)

    def add_float32(self, val, be=False):
        self._buf.extend(struct.pack(self.__end(be) + 'f', val))
        self.pos = len(self._buf)

    def add_float64(self, val, be=False):
        self._buf.extend(struct.pack(self.__end(be) + 'd', val))
        self.pos = len(self._buf)

    def add_list(self, l, be=False):
        for e in l:
            t = type(e)
            if e == 0:
                self.add_uint8(0)
            elif t is int:
                self.add_uint8(Type.T_INT)
                self.add_int32(e, be)
            elif t is str or t is unicode:
                self.add_uint8(Type.T_STR)
                self.add_string(e)
            elif t is Coord:
                self.add_uint8(Type.T_COORD)
                self.add_int32(e.x, be)
                self.add_int32(e.y, be)
            elif t is bytearray:
                self.add_uint8(Type.T_BYTES)
                if len(e) < 128:
                    self.add_uint8(len(e))
                else:
                    self.add_uint8(0x80)
                    self.add_int32(len(e), be)
                self.add_bytes(e)
            elif t is Color:
                self.add_uint8(Type.T_COLOR)
                self.add_uint8(e.r)
                self.add_uint8(e.g)
                self.add_uint8(e.b)
                self.add_uint8(e.a)
            elif t is float:
                self.add_uint8(Type.T_FLOAT32)
                self.add_float32(e, be)
            else:
                pass  # TODO: Add `double` support

    # TODO: Add `enc` parameter
    def get_string(self):
        s = ''
        while True:
            c = self.get_uint8()
            if c == 0:
                break
            s += chr(c)
        return s

    def get_bytes(self, len):
        res = self._buf[self.pos:self.pos + len]
        self.pos += len
        return res

    def get_remaining(self):
        res = self._buf[self.pos:]
        self.pos = len(self._buf)
        return res

    def get_uint8(self):
        res = self._buf[self.pos]
        self.pos += 1
        return res

    def get_int16(self, be=False):
        res = struct.unpack(
            self.__end(be) + 'h',
            str(self._buf[self.pos:self.pos + 2])
        )[0]
        self.pos += 2
        return res

    def get_uint16(self, be=False):
        res = struct.unpack(
            self.__end(be) + 'H',
            str(self._buf[self.pos:self.pos + 2])
        )[0]
        self.pos += 2
        return res

    def get_int32(self, be=False):
        res = struct.unpack(
            self.__end(be) + 'i',
            str(self._buf[self.pos:self.pos + 4])
        )[0]
        self.pos += 4
        return res

    def get_uint32(self, be=False):
        res = struct.unpack(
            self.__end(be) + 'I',
            str(self._buf[self.pos:self.pos + 4])
        )[0]
        self.pos += 4
        return res

    def get_int64(self, be=False):
        res = struct.unpack(
            self.__end(be) + 'q',
            str(self._buf[self.pos:self.pos + 8])
        )[0]
        self.pos += 8
        return res

    def get_float32(self, be=False):
        res = struct.unpack(
            self.__end(be) + 'f',
            str(self._buf[self.pos:self.pos + 4])
        )[0]
        self.pos += 4
        return res

    def get_float64(self, be=False):
        res = struct.unpack(
            self.__end(be) + 'd',
            str(self._buf[self.pos:self.pos + 8])
        )[0]
        self.pos += 8
        return res

    def get_list(self, be=False):
        res = []
        while True:
            if self.eom():
                break
            t = self.get_uint8()
            if t == Type.T_END:
                break
            elif t == Type.T_INT:
                res.append(self.get_int32(be))
            elif t == Type.T_STR:
                res.append(self.get_string())
            elif t == Type.T_COORD:
                x = self.get_int32(be)
                y = self.get_int32(be)
                res.append(Coord(x, y))
            elif t == Type.T_UINT8:
                res.append(self.get_uint8())
            elif t == Type.T_UINT16:
                res.append(self.get_uint16(be))
            elif t == Type.T_INT8:
                res.append(self.get_uint8())  # TODO
            elif t == Type.T_INT16:
                res.append(self.get_int16(be))
            elif t == Type.T_COLOR:
                r = self.get_uint8()
                g = self.get_uint8()
                b = self.get_uint8()
                a = self.get_uint8()
                res.append(Color(r, g, b, a))
            elif t == Type.T_TTOL:
                res.append(self.get_list(be))
            elif t == Type.T_NIL:
                res.append(0)
            elif t == Type.T_UID:
                res.append(self.get_int64(be))
            elif t == Type.T_BYTES:
                l = self.get_uint8()
                if (l & 128) != 0:
                    l = self.get_int32(be)
                res.append(self.get_bytes(l))
            elif t == Type.T_FLOAT32:
                res.append(self.get_float32(be))
            elif t == Type.T_FLOAT64:
                res.append(self.get_float64(be))
            else:
                pass  # TODO
        return res

    def eom(self):
        return self.pos >= len(self._buf)

    def __str__(self):
        return ', '.join([hex(c) + '/' + chr(c) for c in self._buf])