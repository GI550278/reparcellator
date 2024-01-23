import struct


class DataStreamWriter:

    def __init__(self, payload=bytearray()):
        self.payload = payload
        self.cursor = 0

    def add(self, val):
        self.cursor += val

    def report(self, pos, n=20):
        print([int(b) for b in self.payload[pos:pos + n]])

    def clear(self):
        self.payload = bytearray()
        self.cursor = 0

    def writeBytes(self, bytes):
        self.payload.extend(bytes)
        self.cursor += len(bytes)

    def writeDouble(self, num):
        self.payload.extend(struct.pack('d', num))
        self.add(8)

    def writeUnsignedShort(self, num):
        self.payload.extend(struct.pack('H', num))
        self.add(2)

    def writeFloat(self, num):
        self.payload.extend(struct.pack('f', num))
        self.add(4)

    def writeDoubleArray(self, arr):
        for num in arr:
            self.payload.extend(struct.pack('d', num))
        self.add(len(arr) * 8)

    def writeFloatArray(self, arr):
        for num in arr:
            self.payload.extend(struct.pack('f', num))
        self.add(len(arr) * 4)

    def writeUnsignedLong(self, num):
        self.payload.extend(struct.pack('L', num))
        self.cursor += 4

    def rewriteUnsignedLong(self, pos, num):
        self.payload[pos:pos + 4] = struct.pack('L', num)
        self.cursor += 4

    def writeInt(self, num):
        self.payload.extend(struct.pack('i', num))
        self.cursor += 4

    def writeUnsignedLongLong(self, num):
        self.payload.extend(struct.pack('Q', num))
        self.cursor += 8

    def rewriteUnsignedLongLong(self, pos, num):
        self.payload[pos:pos + 8] = struct.pack('Q', num)

    def writeString(self, s):
        self.writeUnsignedLong(len(s))
        self.payload.extend(s.encode('ascii'))
        self.cursor += len(s)

    def writeBool(self, flag):
        self.payload.extend(struct.pack('?', flag))
        self.add(1)

    def writeKnownSizeString(self, s):
        self.payload.extend(s.encode('ascii'))
        self.cursor += len(s)
