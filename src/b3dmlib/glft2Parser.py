import base64
import struct
import sys
import DracoPy
from pathlib import Path
from pygltflib import GLTF2, BufferView, Accessor, Primitive, Mesh, Texture, Image
from b3dmlib.ComponentType import ComponentType
from b3dmlib.ElementType import ElementType
from meshexchange.ExtendedExchangeFormat import ExtendedExchangeFormat


class glft2Parser:
    def __init__(self, flipTexture=False, Y_UP=True):
        self.cursor = 0
        self.flipTexture = flipTexture
        self.Y_UP = Y_UP
        self.gltf = None
        self.binaryBlob = None

    def toExtendedExchangeFormat(self, imagePath="", imageFile="", writeHint=0, RTC_CENTER=None):
        if RTC_CENTER is None:
            RTC_CENTER = [0, 0, 0]
            if 'CESIUM_RTC' in self.gltf.extensions:
                if 'center' in self.gltf.extensions['CESIUM_RTC']:
                    RTC_CENTER = self.gltf.extensions['CESIUM_RTC']['center']

        if self.gltf.scene == None:
            self.gltf.scene = 0

        nodes_count = len(self.gltf.scenes[self.gltf.scene].nodes)
        parsed = []
        if 'KHR_draco_mesh_compression' in self.gltf.extensionsRequired:
            for n in range(nodes_count):
                parsed.append(self.parseDracoData(n))
        else:
            for n in range(nodes_count):
                parsed.extend(self.parseData(n))

        parts = {'subparts': parsed}

        images_count = len(self.gltf.images)
        images = []
        for n in range(images_count):
            images.append({'imageBlob': self.parseImage(n), 'writeHint': [1, writeHint],
                           'imageFile': imageFile.replace('.jpg', f'_{n}.jpg'),
                           'imagePath': imagePath.replace('.jpg', f'_{n}.jpg')})

        # print('RTC_CENTER:', RTC_CENTER)

        return ExtendedExchangeFormat(parts=[parts], images=images, origin=RTC_CENTER)

    def loadFromBlob(self, blob):
        self.gltf = GLTF2().load_from_bytes(blob)
        self.binaryBlob = self.gltf.binary_blob()

    def load(self, file_name):
        file_path = Path(file_name)
        if file_path.suffix not in ['.gltf', '.glb']:
            raise Exception(f'wrong file extension {file_path.suffix}')
        self.gltf = GLTF2().load(file_name)
        self.binaryBlob = self.gltf.binary_blob()

    def report(self):
        n = len(self.gltf.scenes[self.gltf.scene].nodes)
        print("number of nodes/meshes:", n)
        for k in range(n):
            mesh = self.gltf.meshes[self.gltf.scenes[self.gltf.scene].nodes[k]]
            m = len(mesh.primitives)
            print("mesh ", k)
            print("\t number of primitive", m)
            primitive = mesh.primitives[0]
            material = self.gltf.materials[primitive.material]
            textureIndex = material.pbrMetallicRoughness.baseColorTexture.index
            texture = self.gltf.textures[textureIndex]
            print("\t texture.source=", texture.source)

    def parseDracoData(self, index=0):
        node = self.gltf.nodes[self.gltf.scenes[self.gltf.scene].nodes[index]]
        mesh = self.gltf.meshes[node.mesh]

        if len(mesh.primitives) > 1:
            print('Mesh contain more than one primitive, other primitives are ignored')
            return None

        primitive = mesh.primitives[0]
        if 'KHR_draco_mesh_compression' not in primitive.extensions:
            print('No draco extension detected')
            return None

        compressed = primitive.extensions['KHR_draco_mesh_compression']
        compressed_buffer_view = self.gltf.bufferViews[compressed['bufferView']]
        compressed_data = self.binaryBlob[compressed_buffer_view.byteOffset:(
                compressed_buffer_view.byteOffset + compressed_buffer_view.byteLength)]

        mesh = DracoPy.decode(bytes(compressed_data))

        parsed_data = {}
        parsed_data['material'] = self.gltf.materials[primitive.material]
        parsed_data = self.mesh_to_parsed_data(mesh, parsed_data)

        return parsed_data

    def mesh_to_parsed_data(self, mesh, parsed_data):

        if self.Y_UP:
            parsed_data['vertices'] = list(map(lambda x: [x[0], -x[2], x[1]], mesh.points))
        else:
            parsed_data['vertices'] = list(map(list, mesh.points))
        parsed_data['indices'] = list(map(list, mesh.faces))

        if mesh.tex_coord is None:
            # no image and texture
            parsed_data['imageIndex'] = None
            parsed_data['texCoords'] = None
            return parsed_data

        if 'material' not in parsed_data:
            # no image and texture
            parsed_data['imageIndex'] = None
            parsed_data['texCoords'] = None
            print("No material")
            return parsed_data

        if parsed_data['material'].pbrMetallicRoughness.baseColorTexture is None:
            # no image and texture
            parsed_data['imageIndex'] = None
            parsed_data['texCoords'] = None
            print("No material")
            return parsed_data

        tex_coords = list(map(list, mesh.tex_coord))
        texture_index = parsed_data['material'].pbrMetallicRoughness.baseColorTexture.index
        texture = self.gltf.textures[texture_index]
        if texture.source is None:
            if 'EXT_texture_webp' in texture.extensions:
                parsed_data['imageIndex'] = texture.extensions['EXT_texture_webp']['source']
            else:
                print("No EXT_texture_webp")
                parsed_data['imageIndex'] = None
        else:
            parsed_data['imageIndex'] = texture.source

        if self.flipTexture:
            parsed_data['texCoords'] = []
            for tex in tex_coords:
                parsed_data['texCoords'].append([tex[0], 1 - tex[1]])
        else:
            parsed_data['texCoords'] = tex_coords
        return parsed_data

    def parseData(self, index=0):
        def chunks(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        tex_coords = []
        node = self.gltf.nodes[self.gltf.scenes[self.gltf.scene].nodes[index]]
        mesh = self.gltf.meshes[node.mesh]

        matrix = node.matrix

        # use to get single primitive with texture
        # primitiveIndex = 0
        # if len(mesh.primitives)>1:
        #     while mesh.primitives[primitiveIndex].attributes.TEXCOORD_0 is None and primitiveIndex < len(mesh.primitives):
        #         primitiveIndex += 1
        #     if primitiveIndex >= len(mesh.primitives):
        #         primitiveIndex = 0

        parsedDataArr = []
        for primitive in mesh.primitives:  # [mesh.primitives[primitiveIndex]]:
            parsedData = self.parse_mesh(chunks, matrix, primitive, tex_coords)
            parsedDataArr.append(parsedData)
        return parsedDataArr

    def parse_mesh(self, chunks, matrix, primitive, tex_coords):
        parsedData = {}
        indices = self.parseComponent(primitive.indices)
        vertices = self.parseComponent(primitive.attributes.POSITION)
        if (matrix is not None) and len(matrix) > 0:
            parsedData['vertices'] = list(
                map(lambda x: [x[0] * matrix[0] + x[1] * matrix[4] + x[2] * matrix[8] + matrix[12],
                               x[0] * matrix[1] + x[1] * matrix[5] + x[2] * matrix[9] + matrix[13],
                               x[0] * matrix[2] + x[1] * matrix[6] + x[2] * matrix[10] + matrix[14],
                               x[0] * matrix[3] + x[1] * matrix[7] + x[2] * matrix[11] + matrix[15]]
                    , vertices))

            parsedData['vertices'] = list(map(lambda x: [x[0], -x[2], x[1]], parsedData['vertices']))
        else:
            if self.Y_UP:
                parsedData['vertices'] = list(map(lambda x: [x[0], -x[2], x[1]], vertices))
            else:
                parsedData['vertices'] = vertices
        parsedData['material'] = self.gltf.materials[primitive.material]
        parsedData['indices'] = list(chunks(indices, 3))
        if parsedData['material'].pbrMetallicRoughness.baseColorTexture is None:
            # no image and texture
            parsedData['imageIndex'] = None
            parsedData['texCoords'] = None

        else:
            try:
                texture_index = parsedData['material'].pbrMetallicRoughness.baseColorTexture.index
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()

            texture = self.gltf.textures[texture_index]
            if 'EXT_texture_webp' in texture.extensions:
                parsedData['imageIndex'] = texture.extensions['EXT_texture_webp']['source']
            else:
                parsedData['imageIndex'] = texture.source
            tex_coord = parsedData['material'].pbrMetallicRoughness.baseColorTexture.texCoord
            if tex_coord == 0:
                tex_coords = self.parseComponent(primitive.attributes.TEXCOORD_0)
            elif tex_coord == 1:
                tex_coords = self.parseComponent(primitive.attributes.TEXCOORD_1)

            if self.flipTexture:
                parsedData['texCoords'] = []
                for tex in tex_coords:
                    parsedData['texCoords'].append([tex[0], 1 - tex[1]])
            else:
                parsedData['texCoords'] = tex_coords
        return parsedData

    def parseImage(self, texture_source):
        bufferViewIndex = self.gltf.images[texture_source].bufferView
        if bufferViewIndex is None:
            return base64.decodebytes(
                self.gltf.images[texture_source].uri.replace('data:image/jpeg;base64', '').encode("ascii"))

        bufferView = self.gltf.bufferViews[bufferViewIndex]
        index_start = bufferView.byteOffset
        index_end = bufferView.byteOffset + bufferView.byteLength
        return self.binaryBlob[index_start:index_end]

    def parse(self, index=0):
        # get the first mesh in the current scene (in this example there is only one scene and one mesh)
        mesh = self.gltf.meshes[self.gltf.scenes[self.gltf.scene].nodes[index]]
        parsedData = {'attributes': {}, 'indices': []}

        for primitive in [mesh.primitives[0]]:
            parsedData['indices'] = self.parseComponent(primitive.indices)
            parsedData['POSITION'] = self.parseComponent(primitive.attributes.POSITION)
            # parsedData['attributes']['COLOR_0'] = self.parseComponent(primitive.attributes.COLOR_0)
            # parsedData['attributes']['JOINTS_0'] = self.parseComponent(primitive.attributes.JOINTS_0)
            # parsedData['attributes']['NORMAL'] = self.parseComponent(primitive.attributes.NORMAL)
            # parsedData['attributes']['TANGENT'] = self.parseComponent(primitive.attributes.TANGENT)
            # parsedData['attributes']['WEIGHTS_0'] = self.parseComponent(primitive.attributes.WEIGHTS_0)

            parsedData['material'] = self.gltf.materials[primitive.material]
            textureIndex = parsedData['material'].pbrMetallicRoughness.baseColorTexture.index
            texture = self.gltf.textures[textureIndex]
            bufferViewIndex = self.gltf.images[texture.source].bufferView
            bufferView = self.gltf.bufferViews[bufferViewIndex]
            index_start = bufferView.byteOffset
            index_end = bufferView.byteOffset + bufferView.byteLength
            parsedData['imageBlob'] = self.binaryBlob[index_start:index_end]
            texCoord = parsedData['material'].pbrMetallicRoughness.baseColorTexture.texCoord
            if texCoord == 0:
                parsedData['TEXCOORD'] = self.parseComponent(primitive.attributes.TEXCOORD_0)
            elif texCoord == 1:
                parsedData['TEXCOORD'] = self.parseComponent(primitive.attributes.TEXCOORD_1)
        return parsedData

    def parseComponent(self, accessor_index):
        if accessor_index is None:
            return None
        if accessor_index > len(self.gltf.accessors):
            return None

        accessor = self.gltf.accessors[accessor_index]

        if accessor.bufferView is None:
            return None
        bufferView = self.gltf.bufferViews[accessor.bufferView]

        componentType = ComponentType(accessor.componentType)
        componentTypeSize = componentType.getSize()
        elementTypeSize = ElementType(accessor.type).getSize()
        # todo: support uri
        # buffer = self.gltf.buffers[bufferView.buffer]
        # data_i = self.gltf.decode_data_uri(buffer_i.uri)
        totalSize = componentTypeSize * elementTypeSize
        component = []
        if elementTypeSize == 1:
            for i in range(accessor.count):
                index = bufferView.byteOffset + accessor.byteOffset + i * totalSize
                d_i = self.binaryBlob[index:index + totalSize]
                v_i = struct.unpack(componentType.codeLetter(), d_i)[0]
                component.append(v_i)
        else:
            for i in range(accessor.count):
                index = bufferView.byteOffset + accessor.byteOffset + i * totalSize
                d_i = self.binaryBlob[index:index + totalSize]
                v_i = list(struct.unpack(componentType.codeLetter() * elementTypeSize, d_i))
                component.append(v_i)

        return component

    ###################################################################################################
    def addComponent(self, data, componentType, elementType):
        accessor_index = len(self.gltf.accessors)
        accessor = Accessor()
        self.gltf.accessors.append(accessor)
        accessor.count = len(data)
        accessor.byteOffset = 0
        accessor.componentType = componentType
        accessor.type = elementType

        bufferView = BufferView()
        bufferView.byteOffset = self.cursor
        accessor.bufferView = len(self.gltf.bufferViews)
        self.gltf.bufferViews.append(bufferView)

        componentType = ComponentType(accessor.componentType)
        componentTypeSize = componentType.getSize()
        elementTypeSize = ElementType(accessor.type).getSize()
        totalSize = componentTypeSize * elementTypeSize
        self.cursor += accessor.count * totalSize

        if elementTypeSize == 1:
            for i in range(accessor.count):
                index = bufferView.byteOffset + accessor.byteOffset + i * totalSize
                self.binaryBlob[index:index + totalSize] = struct.pack(componentType.codeLetter(), data[i])
        else:
            for i in range(accessor.count):
                index = bufferView.byteOffset + accessor.byteOffset + i * totalSize
                self.binaryBlob[index:index + totalSize] = \
                    struct.pack(componentType.codeLetter() * elementTypeSize, *data[i])

        return accessor_index

    def addObject(self, list, object):
        index = len(list)
        list.append(object)
        return index

    def loadData(self, parsedData, index):
        primitive = Primitive()
        primitive.attributes.POSITION = self.addComponent(parsedData['vertices'], 5126, 'VEC3')

        texCoords = []
        for tx in parsedData['texCoords']:
            u, v = tx[0], 1 - tx[1]
            texCoords.append([u, v])

        material = parsedData['material']
        texCoord = material.pbrMetallicRoughness.baseColorTexture.texCoord
        if texCoord == 0:
            primitive.attributes.TEXCOORD_0 = self.addComponent(texCoords, 5126, 'VEC2')
        elif texCoord == 1:
            primitive.attributes.TEXCOORD_1 = self.addComponent(texCoords, 5126, 'VEC2')

        textureIndex = material.pbrMetallicRoughness.baseColorTexture.index
        texture = Texture()
        texture.source = parsedData['imageIndex']

        material.pbrMetallicRoughness.baseColorTexture.index = \
            self.addObject(self.gltf.textures, texture)
        primitive.material = self.addObject(self.gltf.materials, material)

        indices = [item for sublist in parsedData['indices'] for item in sublist]
        primitive.indices = self.addComponent(indices, 5125, 'SCALAR')

        mesh = Mesh()
        primitive_index = self.addObject(mesh.primitives, primitive)
        mesh_index = self.addObject(self.gltf.meshes, mesh)
        self.gltf.scene.nodes[index] = mesh_index

    def loadImage(self, imageBlob):
        bufferView = BufferView()
        byteLength = len(imageBlob)
        bufferView.byteOffset = self.cursor
        bufferView.byteLength = byteLength

        index_start = self.cursor
        index_end = self.cursor + byteLength
        self.cursor += byteLength
        self.binaryBlob[index_start:index_end] = imageBlob

        image = Image()
        image.bufferView = bufferView
        texture_source = self.addObject(self.gltf.images, image)

    def toBlob(self):
        pass
