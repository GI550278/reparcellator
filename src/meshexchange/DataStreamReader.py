import struct


class DataStreamReader:
    def __init__(self, payload=bytearray()):
        self.payload = payload
        self.cursor = 0

    def set(self, payload):
        self.payload = payload
        self.cursor = 0

    def setCursor(self, cursor):
        self.cursor = cursor

    def add(self, val):
        self.cursor += val

    def readStringKnownSize(self, size: int) -> str:
        name = struct.unpack(str(size) + 's', self.payload[self.cursor:self.cursor + size])[0].decode("utf-8")
        self.add(size)
        return name

    def readString(self) -> str:
        s = struct.unpack('L', self.payload[self.cursor:self.cursor + 4])[0]
        self.add(4)
        name = self.payload[self.cursor:(self.cursor + s)].decode("ascii")
        self.add(s)
        return name

    def readUnsignedInt(self) -> int:
        s = struct.unpack('I', self.payload[self.cursor:self.cursor + 4])[0]
        self.add(4)
        return s

    def readInt(self) -> int:
        s = struct.unpack('i', self.payload[self.cursor:self.cursor + 4])[0]
        self.add(4)
        return s

    def readUnsignedLong(self) -> int:
        s = struct.unpack('L', self.payload[self.cursor:self.cursor + 4])[0]
        self.add(4)
        return s

    def readUnsignedShort(self) -> int:
        s = struct.unpack('H', self.payload[self.cursor:self.cursor + 2])[0]
        self.add(2)
        return s

    def readFloat(self) -> float:
        s = struct.unpack('f', self.payload[self.cursor:self.cursor + 4])[0]
        self.add(4)
        return s

    def readBool(self) -> bool:
        s = struct.unpack('?', self.payload[self.cursor:self.cursor + 1])[0]
        self.add(1)
        return s

    def readUnsignedLongLong(self) -> int:
        s = struct.unpack('Q', self.payload[self.cursor:self.cursor + 8])[0]
        self.add(8)
        return s

    def report(self, n=20):
        print([int(b) for b in self.payload[self.cursor:self.cursor + n]])
    def reportAsString(self, n=20):
        print(''.join([chr(b) for b in self.payload[self.cursor:self.cursor + n]]))


    def areNextBytes(self, bytes):
        n = len(bytes)
        for k in range(n):
            if bytes[k] != self.payload[self.cursor + k]:
                return False
        return True

    def verifyBytes(self, bytes):
        n = len(bytes)
        for k in range(n):
            if bytes[k] != self.payload[self.cursor + k]:
                raise Exception("Error unexpected byte values")
        self.add(n)

    def readByteArray(self, s):
        arr = [int(x) for x in self.payload[self.cursor:self.cursor + s]]
        self.add(len(arr))
        return arr

    def readDoubleArray(self, s):
        arr = [0] * s
        for k in range(s):
            arr[k] = struct.unpack('d', self.payload[
                                        self.cursor + 8 * k:self.cursor + 8 * k + 8])[0]
        self.add(s * 8)
        return arr

    def readFloatArray(self, s):
        arr = [0] * s
        for k in range(s):
            arr[k] = struct.unpack('f', self.payload[
                                        self.cursor + 4 * k:self.cursor + 4 * k + 4])[0]
        self.add(s * 4)
        return arr

    def verifySize(self, c, s):
        if self.cursor != c + s:
            raise Exception("Error, wrong size")

    def readStringArray(self):
        arrSize = self.readUnsignedLong()
        totalSize = self.readUnsignedLongLong() - 8
        # 8 + 4 * arrSize
        arr = []
        for index in range(arrSize):
            arr.append(self.readString())
            totalSize -= len(arr[index]) + 4
        if totalSize != 0:
            raise Exception("Error, wrong string array size")
        return arr

    def readStringArrayNoTotal(self):
        arrSize = self.readUnsignedLong()
        arr = []
        for index in range(arrSize):
            arr.append(self.readString())
        return arr

    def reportString(self, n=20):
        print(self.payload[self.cursor:self.cursor + n])

    def readFloatPairsArray(self):
        rangeListSize = self.readUnsignedLong()
        arr = [0] * rangeListSize
        rangeListGutSize = self.readUnsignedLongLong()
        if (8 + 8 * rangeListSize) != rangeListGutSize:
            print(rangeListSize, rangeListGutSize)
            raise Exception("Error reading PagedLOD, wrong rangeListGutSize")
        for k in range(rangeListSize):
            x0 = self.readFloat()
            x1 = self.readFloat()
            arr[k] = [x0, x1]
        return arr

    def readFloatPairsArrayNoGut(self):
        rangeListSize = self.readUnsignedLong()
        arr = [0] * rangeListSize
        for k in range(rangeListSize):
            x0 = self.readFloat()
            x1 = self.readFloat()
            arr[k] = [x0, x1]
        return arr

    def readUnsignedLongArrayArray(self):
        arraySize = self.readUnsignedLong()
        arr = [0] * arraySize
        totalSize = self.readUnsignedLongLong() - 8
        for h in range(arraySize):
            itemSize = self.readUnsignedLong()
            arr[h] = [[0, 0]] * itemSize
            for k in range(itemSize):
                totalSize -= 2 * 4 + 4
                for j in range(2):
                    x = self.readUnsignedLong()
                    arr[h][k][j] = x

        if totalSize != 0:
            raise Exception("Error reading pair array, wrong size")
        return arr
