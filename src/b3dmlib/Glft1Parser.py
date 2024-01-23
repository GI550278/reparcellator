"""
Used to parse gltf version 1 file
"""

import json
import struct
from b3dmlib.ComponentType import ComponentType
from b3dmlib.ElementType import ElementType
from meshexchange.ExtendedExchangeFormat import ExtendedExchangeFormat


class Glft1Parser:
    def __init__(self, flipTexture=False, Y_UP=False):
        self.cursor = 0
        self.binaryBlob = None
        self.flipTexture = flipTexture
        self.scene_data = {}
        self.Y_UP = Y_UP

    def loadFromBlob(self, blob):
        magic = struct.unpack("<BBBB", blob[:4])
        version, _ = struct.unpack("<II", blob[4:12])
        expected_magic = b'glTF'
        if bytearray(magic) != expected_magic:
            raise IOError("Unable to load binary gltf file. Header does not appear to be valid glb format.")
        if version != 1:
            raise IOError("Only version 1 of glFT is supported")
        index = 12
        scene_length, scene_format = struct.unpack("<II", blob[index:index + 8])
        index += 8
        if scene_format == 0:  # JSON
            raw_json = blob[index:index + scene_length].decode("utf-8")
            self.scene_data = json.loads(raw_json)
            index += scene_length
        else:
            raise IOError("not a JSON glTF header")

        self.binaryBlob = blob[index:]

    def toExtendedExchangeFormat(self, imagePath="", imageFile="", writeHint=0, RTC_CENTER=None):
        if 'extensions' in self.scene_data:
            if 'CESIUM_RTC' in self.scene_data['extensions']:
                if 'center' in self.scene_data['extensions']['CESIUM_RTC']:
                    RTC_CENTER = self.scene_data['extensions']['CESIUM_RTC']['center']

        nodes_count = len(self.scene_data['scenes'][self.scene_data['scene']]['nodes'])

        parsed = []
        for n in range(nodes_count):
            one_parsed = self.parseData(n)
            if one_parsed == None:
                continue
            parsed.append(one_parsed)
        if 'images' in self.scene_data:
            images_count = len(self.scene_data['images'])
        else:
            images_count = 0

        # print(self.scene_data['images'])
        images = []
        for n in range(images_count):
            images.append({'imageBlob': self.parseImage(n), 'writeHint': [1, writeHint],
                           'imageFile': imageFile.replace('.jpg', f'_{n}.jpg'),
                           'imagePath': imagePath.replace('.jpg', f'_{n}.jpg')})
        parts = {}
        parts['subparts'] = parsed
        parts['children'] = []
        return ExtendedExchangeFormat(parts=[parts], images=images, origin=RTC_CENTER)

    def parseComponent(self, accessor_index):
        if accessor_index not in self.scene_data['accessors'].keys():
            return None

        accessor = self.scene_data['accessors'][accessor_index]
        bufferView = self.scene_data['bufferViews'][accessor['bufferView']]

        componentType = ComponentType(accessor['componentType'])
        componentTypeSize = componentType.getSize()
        elementTypeSize = ElementType(accessor['type']).getSize()
        # todo: support uri
        # buffer = self.gltf.buffers[bufferView.buffer]
        # data_i = self.gltf.decode_data_uri(buffer_i.uri)
        totalSize = componentTypeSize * elementTypeSize
        component = []
        if elementTypeSize == 1:
            for i in range(accessor['count']):
                index = bufferView['byteOffset'] + accessor['byteOffset'] + i * totalSize
                d_i = self.binaryBlob[index:index + totalSize]
                v_i = struct.unpack(componentType.codeLetter(), d_i)[0]
                component.append(v_i)
        else:
            for i in range(accessor['count']):
                index = bufferView['byteOffset'] + accessor['byteOffset'] + i * totalSize
                d_i = self.binaryBlob[index:index + totalSize]
                v_i = list(struct.unpack(componentType.codeLetter() * elementTypeSize, d_i))
                component.append(v_i)

        return component

    def parseData(self, index):
        def chunks(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        root_node = self.scene_data['nodes'][self.scene_data['scenes']\
            [self.scene_data['scene']]['nodes'][index]]
        if 'children' in root_node:
            child_node = self.scene_data['nodes'][root_node['children'][0]]
        else:
            child_node = root_node

        if not 'meshes' in self.scene_data or not 'meshes' in child_node:
            return None
        parsedData = {}

        if 'matrix' in child_node:
            parsedData['matrix'] = child_node['matrix']

        mesh = self.scene_data['meshes'][child_node['meshes'][0]]

        for primitive in [mesh['primitives'][0]]:
            indices = self.parseComponent(primitive['indices'])

            parsedData['indices'] = list(chunks(indices, 3))
            parsedData['vertices'] = self.parseComponent(primitive['attributes']['POSITION'])
            if self.Y_UP:
                parsedData['vertices'] = list(map(lambda x: [x[0], -x[2], x[1]], parsedData['vertices']))

            parsedData['material'] = self.scene_data['materials'][primitive['material']]
            # technique = self.scene_data['techniques'][parsedData['material']['technique']]
            parsedData['imageIndex'] = 0  # how the mesh is connected to the textures ? what is the texture index ?
            texCoords = self.parseComponent(primitive['attributes']['TEXCOORD_0'])
            if self.flipTexture:
                parsedData['texCoords'] = []
                for tx in texCoords:
                    u, v = tx[0], 1 - tx[1]
                    parsedData['texCoords'].append([u, v])
            else:
                parsedData['texCoords'] = texCoords
        return parsedData

    def parseImage(self, index):
        image = self.scene_data['images'][list(self.scene_data['images'].keys())[index]]
        binary_glTF = image['extensions']['KHR_binary_glTF']
        bufferViewIndex = binary_glTF['bufferView']
        bufferView = self.scene_data['bufferViews'][bufferViewIndex]
        # print(bufferView)
        # print(binary_glTF)
        # self.scene_data['buffers']
        index_start = bufferView['byteOffset']
        index_end = bufferView['byteOffset'] + bufferView['byteLength']
        return self.binaryBlob[index_start:index_end]
