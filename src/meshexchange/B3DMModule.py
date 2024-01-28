import os

from b3dmlib.GltfWriter import GltfWriter
from meshexchange.BinaryFile import BinaryFile
from meshexchange.DataStreamReader import DataStreamReader
from meshexchange.DataStreamWriter import DataStreamWriter
from b3dmlib.TileType import TileType
from b3dmlib.glft2Parser import glft2Parser
from b3dmlib.Glft1Parser import Glft1Parser
from meshexchange.ExtendedExchangeFormat import ExtendedExchangeFormat
import json
from pygltflib import GLTF2, Scene, BufferFormat
import struct


class B3DMModule:

    def replaceGlft(self, in_filename, out_filename, gltf, imageFile="", writeHint=0):

        glb_structure = gltf.save_to_bytes()
        gltf_bytes = bytearray()
        for data in glb_structure:
            gltf_bytes.extend(bytes(data))
        gltf_size = len(gltf_bytes)

        dsw = DataStreamWriter(bytearray())

        bf = BinaryFile(in_filename)
        payload = bf.read_all()
        dsr = DataStreamReader(payload)

        magic_value = dsr.readStringKnownSize(4)
        if magic_value != "b3dm":
            raise RuntimeError("Unexpected magic value:", magic_value)
            # print('Error bad magic value, expected b3dm')
            # return None
        dsw.writeKnownSizeString('b3dm')

        tile_type = TileType.BATCHED3DMODEL
        version = dsr.readInt()
        dsw.writeInt(version)

        tile_byte_length = dsr.readInt()
        feature_table_json_len = dsr.readInt()
        feature_table_bin_len = dsr.readInt()
        feature_table_len = feature_table_bin_len + feature_table_json_len
        batch_table_json_len = dsr.readInt()
        batch_table_bin_len = dsr.readInt()
        batch_table_len = batch_table_bin_len + batch_table_json_len
        # dsr.add(feature_table_len)
        feature_table_json = dsr.readStringKnownSize(feature_table_json_len)
        batch_table_json = dsr.readStringKnownSize(batch_table_len)

        tile_byte_length = dsr.cursor + gltf_size
        dsw.writeInt(tile_byte_length)
        dsw.writeInt(feature_table_json_len)
        dsw.writeInt(feature_table_bin_len)
        dsw.writeInt(batch_table_json_len)
        dsw.writeInt(batch_table_bin_len)

        dsw.writeKnownSizeString(feature_table_json)
        dsw.writeKnownSizeString(batch_table_json)
        dsw.writeBytes(gltf_bytes)

        bf = BinaryFile(file_name=out_filename)
        bf.write_all(dsw.payload)

    def extractGltf(self, filename):
        bf = BinaryFile(filename)
        payload = bf.read_all()
        dsr = DataStreamReader(payload)

        magic_value = dsr.readStringKnownSize(4)
        if magic_value != "b3dm":
            ee = ExtendedExchangeFormat()
            ee.parts[0]['subparts'][0]['matrix'] = [1, 0, 0, 0,
                                                    0, 1, 0, 0,
                                                    0, 0, 1, 0,
                                                    0, 0, 0, 1]
            return ee

            # raise RuntimeError("Unexpected magic value:", magic_value)
        tile_type = TileType.BATCHED3DMODEL
        version = dsr.readInt()

        tile_byte_length = dsr.readInt()
        feature_table_json_len = dsr.readInt()
        feature_table_bin_len = dsr.readInt()
        feature_table_len = feature_table_bin_len + feature_table_json_len
        batch_table_json_len = dsr.readInt()
        batch_table_bin_len = dsr.readInt()
        batch_table_len = batch_table_bin_len + batch_table_json_len
        # dsr.add(feature_table_len)
        s = dsr.readStringKnownSize(feature_table_json_len)

        dsr.add(batch_table_len)
        gltf_data = dsr.payload[dsr.cursor:tile_byte_length]

        magic = struct.unpack("<BBBB", gltf_data[:4])
        if bytearray(magic) != b'glTF':
            raise IOError("Unable to load binary gltf file. Header does not appear to be valid glft format.")
        version, length = struct.unpack("<II", gltf_data[4:12])

        if version == 1:
            gltf = Glft1Parser()
        elif version == 2:
            gltf = glft2Parser()
        else:
            raise IOError("Only version 1 or 2 of glFT is supported")

        gltf.loadFromBlob(gltf_data)

        if version == 1:
            return gltf.scene_data
        elif version == 2:
            return gltf.gltf

    def b3dmToExtendedExchange(self, filename, imagePath="", imageFile="", writeHint=0, Y_UP=False):
        bf = BinaryFile(filename)
        payload = bf.read_all()
        return self.b3dmPayloadToExtendedExchange(payload, imagePath, imageFile, writeHint, Y_UP)

    def b3dmPayloadToExtendedExchange(self, payload, imagePath="", imageFile="", writeHint=0, Y_UP=False):
        dsr = DataStreamReader(payload)

        magic_value = dsr.readStringKnownSize(4)
        if magic_value != "b3dm":
            ee = ExtendedExchangeFormat()
            ee.parts[0]['subparts'][0]['matrix'] = [1, 0, 0, 0,
                                                    0, 1, 0, 0,
                                                    0, 0, 1, 0,
                                                    0, 0, 0, 1]
            return ee

            # raise RuntimeError("Unexpected magic value:", magic_value)
        tile_type = TileType.BATCHED3DMODEL
        version = dsr.readInt()

        tile_byte_length = dsr.readInt()
        feature_table_json_len = dsr.readInt()
        feature_table_bin_len = dsr.readInt()
        feature_table_len = feature_table_bin_len + feature_table_json_len
        batch_table_json_len = dsr.readInt()
        batch_table_bin_len = dsr.readInt()
        batch_table_len = batch_table_bin_len + batch_table_json_len
        # dsr.add(feature_table_len)
        s = dsr.readStringKnownSize(feature_table_json_len)
        if len(s) == 0:
            RTC_CENTER = [0, 0, 0]
        else:
            feature_table_json = json.loads(s)
            if 'RTC_CENTER' in feature_table_json:
                RTC_CENTER = feature_table_json['RTC_CENTER']
            else:
                RTC_CENTER = None
        dsr.add(batch_table_len)
        gltf_data = dsr.payload[dsr.cursor:tile_byte_length]

        magic = struct.unpack("<BBBB", gltf_data[:4])
        if bytearray(magic) != b'glTF':
            raise IOError("Unable to load binary gltf file. Header does not appear to be valid glft format.")
        version, length = struct.unpack("<II", gltf_data[4:12])

        if version == 1:
            gltf = Glft1Parser(Y_UP=Y_UP)
        elif version == 2:
            gltf = glft2Parser(Y_UP=Y_UP)
        else:
            raise IOError("Only version 1 or 2 of glFT is supported")

        if writeHint == 1 or writeHint == 2:
            gltf.flipTexture = True
        elif writeHint == 0:
            gltf.flipTexture = False

        gltf.loadFromBlob(gltf_data)

        ee = gltf.toExtendedExchangeFormat(imagePath, imageFile, writeHint, RTC_CENTER)

        return ee

    def removeFiles(self, fileName):
        glb = fileName + ".glb"
        if os.path.exists(glb):
            os.remove(glb)

        b3dm = fileName + ".b3dm"
        if os.path.exists(b3dm):
            os.remove(b3dm)

    def extendedExchangeTob3dm(self, ee, fileName):
        self.removeFiles(fileName)

        gltf_writer = GltfWriter()
        gltf_writer.fromExtendedExchangeFormatToGlbOneBuffer(ee, False)
        gltf_writer.newGLTF.extensionsUsed = ['CESIUM_RTC']
        gltf_writer.newGLTF.extensions = {'CESIUM_RTC': {'center': ee.origin}}
        gltf = gltf_writer.newGLTF

        glb_structure = gltf.save_to_bytes()
        gltf_bytes = bytearray()
        for data in glb_structure:
            gltf_bytes.extend(bytes(data))
        gltf_size = len(gltf_bytes)

        bf = BinaryFile(fileName + ".glb")

        bf.write_all(gltf_bytes)

        pad = gltf_size % 8
        # print('o' * 80)
        # print(gltf_size, pad)
        if pad > 0:
            gltf_bytes += bytearray([0] * (8 - pad))
        gltf_size = len(gltf_bytes)
        # print(gltf_size, gltf_size % 8)

        version = 1

        feature_table_json = {'BATCH_LENGTH': 0}
        # feature_table_json = {'BATCH_LENGTH': 0, 'RTC_CENTER': ee.origin}
        # feature_table_json = {}
        featureTable = json.dumps(feature_table_json)
        featureTableJSONByteLength = len(featureTable)

        pad = featureTableJSONByteLength % 8
        # print('q' * 80)
        # print(featureTableJSONByteLength, pad)
        if pad > 0:
            featureTable += ' ' * (8 - pad)
        featureTableJSONByteLength = len(featureTable)
        # print(featureTableJSONByteLength, featureTableJSONByteLength % 8)

        featureTableBinaryByteLength = 0
        batchTableJSONByteLength = 0
        batchTableBinaryByteLength = 0
        byteLength = 28 + featureTableJSONByteLength + \
                     featureTableBinaryByteLength + \
                     batchTableJSONByteLength + \
                     batchTableBinaryByteLength + gltf_size

        dsw = DataStreamWriter()
        dsw.clear()
        dsw.writeKnownSizeString("b3dm")
        dsw.writeUnsignedLong(version)
        dsw.writeUnsignedLong(byteLength)
        dsw.writeUnsignedLong(featureTableJSONByteLength)
        dsw.writeUnsignedLong(featureTableBinaryByteLength)
        dsw.writeUnsignedLong(batchTableJSONByteLength)
        dsw.writeUnsignedLong(batchTableBinaryByteLength)
        dsw.writeKnownSizeString(featureTable)
        dsw.writeBytes(gltf_bytes)

        bf = BinaryFile(fileName + ".b3dm")
        bf.write_all(dsw.payload)
