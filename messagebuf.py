import struct


class MessageBuf:
    def __init__(self, buf=bytearray()):
        self._buf = bytearray(buf)
        self.pos = 0

    @property
    def buf(self):
        return self._buf

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

    def add_int16(self, val):
        self._buf.extend(struct.pack('>h', val))
        self.pos = len(self._buf)

    def add_uint16(self, val):
        self._buf.extend(struct.pack('>H', val))
        self.pos = len(self._buf)

    def add_int32(self, val):
        self._buf.extend(struct.pack('>i', val))
        self.pos = len(self._buf)

    def add_uint32(self, val):
        self._buf.extend(struct.pack('>I', val))
        self.pos = len(self._buf)

    def add_float32(self, val):
        self._buf.extend(struct.pack('>f', val))
        self.pos = len(self._buf)

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

    def get_int16(self):
        res = struct.unpack(
            '>h',
            str(self._buf[self.pos:self.pos + 2])
        )[0]
        self.pos += 2
        return res

    def get_uint16(self):
        res = struct.unpack(
            '>H',
            str(self._buf[self.pos:self.pos + 2])
        )[0]
        self.pos += 2
        return res

    def get_int32(self):
        res = struct.unpack(
            '>i',
            str(self._buf[self.pos:self.pos + 4])
        )[0]
        self.pos += 4
        return res

    def get_uint32(self):
        res = struct.unpack(
            '>I',
            str(self._buf[self.pos:self.pos + 4])
        )[0]
        self.pos += 4
        return res

    def get_float32(self):
        res = struct.unpack(
            '>f',
            str(self._buf[self.pos:self.pos + 4])
        )[0]
        self.pos += 4
        return res

    def eom(self):
        return self.pos >= len(self._buf)

    def __str__(self):
        return ', '.join([hex(c) + '/' + chr(c) for c in self._buf])