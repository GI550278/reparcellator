class BinaryFile:
    def __init__(self, file_name: str):
        self.file_name = file_name

    def read_all(self):
        """
            :returns the entire file as bytearray
        """
        with open(self.file_name, "rb") as binaryfile:
            output = bytearray(binaryfile.read())
        return output

    def write_all(self, ba: bytearray):
        with open(self.file_name, "wb") as newFile:
            newFile.write(ba)


