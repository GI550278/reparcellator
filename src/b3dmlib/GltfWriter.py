from pygltflib import GLTF2, BufferView, Accessor, Primitive, Attributes, Mesh, Buffer, Material, \
    PbrMetallicRoughness, Node, Scene, TextureInfo, Image, Texture, ImageFormat, FLOAT, VEC3, VEC2, UNSIGNED_SHORT, \
    SCALAR, UNSIGNED_INT

import struct
import base64
import operator
from io import BytesIO
from PIL import Image as PILImage


class GltfWriter:
    def __init__(self):
        self.newGLTF = GLTF2()

    # https://gitlab.com/dodgyville/pygltflib#a-simple-mesh

    def fromExtendedExchangeFormatToGlbOneBuffer(self, e, flip_yz=False):

        totalSize = 0
        totalBuffer = bytearray()

        buffer_index = len(self.newGLTF.buffers)

        for subpart in range(len(e.parts[0]['subparts'])):
            part = e.parts[0]['subparts'][subpart]
            name = 'part_' + str(subpart)

            # for subpart
            if flip_yz:
                vertices = list(map(lambda x: [x[0], x[2], -x[1]], part['vertices']))
            else:
                vertices = list(part['vertices'])
            if type(part['indices'][0][0]) == int:
                polygons = list(part['indices'])
            else:
                polygons = list(map(lambda x: [x[0].item(), x[1].item(), x[2].item()], part['indices']))

            if not part['texCoords'] is None:
                tex_coords = list(part['texCoords'])
            else:
                tex_coords = None

            flat_polygons = [val for sublist in polygons for val in sublist]

            vertex_bytearray = bytearray()
            for vertex in vertices:
                vertex_bytearray.extend(struct.pack('<fff', vertex[0], vertex[1], vertex[2]))
            vertex_size = len(bytes(vertex_bytearray))


            ind_bytearray = bytearray()

            if max(flat_polygons) < 0xffff:
                flat_polygons_type = UNSIGNED_SHORT
                flat_polygons_pack_type = 'H'
            else:
                flat_polygons_type = UNSIGNED_INT
                flat_polygons_pack_type = 'I'

            for i in flat_polygons:
                ind_bytearray.extend(struct.pack(flat_polygons_pack_type, i))
            ind_size = len(bytes(ind_bytearray))

            tex_coords_bytearray = bytearray()
            tex_coords_size = 0
            if tex_coords is not None:
                for vt in tex_coords:
                    tex_coords_bytearray.extend(struct.pack('<ff', vt[0], vt[1]))
                tex_coords_size = len(bytes(tex_coords_bytearray))

            # buffer view #0
            bw = BufferView(target=None, byteOffset=totalSize, byteLength=vertex_size, byteStride=12,
                            buffer=buffer_index)
            bw_index = len(self.newGLTF.bufferViews)
            self.newGLTF.bufferViews.append(bw)
            totalSize += vertex_size
            totalBuffer.extend(vertex_bytearray)

            mins = [min([operator.itemgetter(i)(vertex) for vertex in vertices]) for i in range(3)]
            maxs = [max([operator.itemgetter(i)(vertex) for vertex in vertices]) for i in range(3)]
            ac = Accessor(bufferView=bw_index, byteOffset=0, componentType=FLOAT, count=len(vertices), max=maxs,
                          min=mins,
                          type=VEC3)
            position_index = len(self.newGLTF.accessors)
            self.newGLTF.accessors.append(ac)

            # buffer view #1

            bw2 = BufferView(target=None, byteOffset=totalSize, byteLength=ind_size, buffer=buffer_index)
            bw2_index = len(self.newGLTF.bufferViews)
            self.newGLTF.bufferViews.append(bw2)
            totalSize += ind_size
            totalBuffer.extend(ind_bytearray)

            maxs = [max(flat_polygons)]
            mins = [min(flat_polygons)]


            aci = Accessor(bufferView=bw2_index, byteOffset=0, componentType=flat_polygons_type, count=len(flat_polygons),
                           max=maxs,
                           min=mins,
                           type=SCALAR)
            indices_index = len(self.newGLTF.accessors)
            self.newGLTF.accessors.append(aci)

            if tex_coords is not None:
                bw3 = BufferView(target=None,
                                 byteOffset=totalSize,
                                 byteLength=tex_coords_size,
                                 buffer=buffer_index)
                bw3_index = len(self.newGLTF.bufferViews)
                self.newGLTF.bufferViews.append(bw3)
                totalSize += tex_coords_size
                totalBuffer.extend(tex_coords_bytearray)

                mins = [min([float(vt[i]) for vt in tex_coords]) for i in range(2)]
                maxs = [max([float(vt[i]) for vt in tex_coords]) for i in range(2)]
                ac = Accessor(bufferView=bw3_index, byteOffset=0, componentType=FLOAT, count=len(tex_coords), max=maxs,
                              min=mins,
                              type=VEC2)
                texcoord_index = len(self.newGLTF.accessors)
                self.newGLTF.accessors.append(ac)

                imageIndex = part['imageIndex']
                imageBlob = e.images[imageIndex]['imageBlob']
                imageFileName = 'C:/temp/temp_text_' + str(subpart) + '.jpg'
                blob = BytesIO(imageBlob)
                pil_img = PILImage.open(blob)
                pil_img.save(imageFileName, format='JPEG', compression="jpeg")

                img = Image(mimeType='image/jpeg', name='tex', uri=imageFileName)
                image_index = len(self.newGLTF.images)
                self.newGLTF.images.append(img)

                texture = Texture(source=image_index)
                self.newGLTF.textures.append(texture)
                baseColorTexture = TextureInfo(index=image_index, texCoord=0)
                color = [0.8, 0.8, 0.8, 1]
                pbr = PbrMetallicRoughness(baseColorFactor=color, baseColorTexture=baseColorTexture, metallicFactor=0,
                                           roughnessFactor=1)
                m = Material(alphaCutoff=0.5, alphaMode='OPAQUE', doubleSided=False, emissiveFactor=[0, 0, 0],
                             emissiveTexture=None,
                             name=name, pbrMetallicRoughness=pbr)

            else:
                texcoord_index = None
                color = [0.8, 0.8, 0.8, 1]
                pbr = PbrMetallicRoughness(baseColorFactor=color, metallicFactor=0,
                                           roughnessFactor=1)
                m = Material(alphaCutoff=0.5, alphaMode='OPAQUE', doubleSided=False, emissiveFactor=[0, 0, 0],
                             emissiveTexture=None,
                             name=name, pbrMetallicRoughness=pbr)

            material_index = len(self.newGLTF.materials)
            self.newGLTF.materials.append(m)

            at = Attributes(POSITION=position_index, TEXCOORD_0=texcoord_index)
            pr = Primitive(attributes=at, material=material_index, mode=4, indices=indices_index)
            me = Mesh()
            me.primitives.append(pr)
            mesh_index = len(self.newGLTF.meshes)
            self.newGLTF.meshes.append(me)

            n = Node(mesh=mesh_index)
            self.newGLTF.nodes.append(n)

        s = Scene(nodes=list(range(len(self.newGLTF.nodes))))
        self.newGLTF.scenes.append(s)
        self.newGLTF.convert_images(ImageFormat.DATAURI)

        q = totalSize % 4
        padding = (4 - q) if q > 0 else 0
        totalSize_padded = totalSize + padding
        self.newGLTF.set_binary_blob(totalBuffer + bytearray([0] * padding))

        bf = Buffer(byteLength=totalSize_padded, uri=None)
        self.newGLTF.buffers.append(bf)

    def fromExtendedExchangeFormatToGlb(self, e):

        # totalSize = 0
        # totalBuffer = bytearray()
        # for subpart in range(len(e.parts[0]['subparts'])):
        for subpart in range(1):
            part = e.parts[0]['subparts'][subpart]
            name = 'part_' + str(subpart)

            # for subpart
            vertices = list(part['vertices'])
            if type(part['indices'][0][0]) == int:
                polygons = list(part['indices'])
            else:
                polygons = list(map(lambda x: [x[0].item(), x[1].item(), x[2].item()], part['indices']))

            if not part['texCoords'] is None:
                tex_coords = list(part['texCoords'])
            else:
                tex_coords = None

            flat_polygons = [val for sublist in polygons for val in sublist]

            vertex_bytearray = bytearray()
            for vertex in vertices:
                vertex_bytearray.extend(struct.pack('<fff', vertex[0], vertex[1], vertex[2]))
            vertex_size = len(bytes(vertex_bytearray))

            ind_bytearray = bytearray()
            for i in flat_polygons:
                ind_bytearray.extend(struct.pack('h', i))
            ind_size = len(bytes(ind_bytearray))

            tex_coords_bytearray = bytearray()
            if tex_coords is not None:
                for vt in tex_coords:
                    tex_coords_bytearray.extend(struct.pack('<ff', vt[0], vt[1]))
            tex_coords_size = len(bytes(tex_coords_bytearray))

            totalSize = vertex_size + ind_size + tex_coords_size
            q = totalSize % 4
            padding = 4 - q if q > 0 else 0
            bf = Buffer(byteLength=(totalSize + padding), uri=None)
            buffer_index = len(self.newGLTF.buffers)
            self.newGLTF.buffers.append(bf)
            self.newGLTF.set_binary_blob(
                vertex_bytearray + ind_bytearray + tex_coords_bytearray + bytearray([0] * padding))

            # buffer view #0
            bw = BufferView(target=None, byteOffset=0, byteLength=vertex_size, byteStride=12, buffer=buffer_index)
            bw_index = len(self.newGLTF.bufferViews)
            self.newGLTF.bufferViews.append(bw)

            mins = [min([vertex[i] for vertex in vertices]) for i in range(3)]
            maxs = [max([vertex[i] for vertex in vertices]) for i in range(3)]
            ac = Accessor(bufferView=bw_index, byteOffset=0, componentType=FLOAT, count=len(vertices), max=maxs,
                          min=mins,
                          type=VEC3)
            position_index = len(self.newGLTF.accessors)
            self.newGLTF.accessors.append(ac)

            # buffer view #1

            bw2 = BufferView(target=None, byteOffset=vertex_size, byteLength=ind_size, buffer=buffer_index)
            bw2_index = len(self.newGLTF.bufferViews)
            self.newGLTF.bufferViews.append(bw2)
            maxs = [max(flat_polygons)]
            mins = [min(flat_polygons)]
            aci = Accessor(bufferView=bw2_index, byteOffset=0, componentType=UNSIGNED_SHORT, count=len(flat_polygons),
                           max=maxs,
                           min=mins,
                           type=SCALAR)
            indices_index = len(self.newGLTF.accessors)
            self.newGLTF.accessors.append(aci)

            if tex_coords is not None:
                bw3 = BufferView(target=None,
                                 byteOffset=vertex_size + ind_size,
                                 byteLength=tex_coords_size,
                                 buffer=buffer_index)
                bw3_index = len(self.newGLTF.bufferViews)
                self.newGLTF.bufferViews.append(bw3)

                mins = [min([vt[i] for vt in tex_coords]) for i in range(2)]
                maxs = [max([vt[i] for vt in tex_coords]) for i in range(2)]
                ac = Accessor(bufferView=bw3_index, byteOffset=0, componentType=FLOAT, count=len(tex_coords), max=maxs,
                              min=mins,
                              type=VEC2)
                texcoord_index = len(self.newGLTF.accessors)
                self.newGLTF.accessors.append(ac)

                imageIndex = part['imageIndex']
                imageBlob = e.images[imageIndex]['imageBlob']
                imageFileName = 'C:/temp/temp_text_' + str(subpart) + '.jpg'
                blob = BytesIO(imageBlob)
                pil_img = PILImage.open(blob)
                pil_img.save(imageFileName, format='JPEG', compression="jpeg")

                img = Image(mimeType='image/jpeg', name='tex', uri=imageFileName)
                image_index = len(self.newGLTF.images)
                self.newGLTF.images.append(img)

                texture = Texture(source=image_index)
                self.newGLTF.textures.append(texture)
                baseColorTexture = TextureInfo(index=image_index, texCoord=0)
                color = [0.8, 0.8, 0.8, 1]
                pbr = PbrMetallicRoughness(baseColorFactor=color, baseColorTexture=baseColorTexture, metallicFactor=0,
                                           roughnessFactor=1)
                m = Material(alphaCutoff=0.5, alphaMode='OPAQUE', doubleSided=False, emissiveFactor=[0, 0, 0],
                             emissiveTexture=None,
                             name=name, pbrMetallicRoughness=pbr)

            else:
                texcoord_index = None
                color = [0.8, 0.8, 0.8, 1]
                pbr = PbrMetallicRoughness(baseColorFactor=color, metallicFactor=0,
                                           roughnessFactor=1)
                m = Material(alphaCutoff=0.5, alphaMode='OPAQUE', doubleSided=False, emissiveFactor=[0, 0, 0],
                             emissiveTexture=None,
                             name=name, pbrMetallicRoughness=pbr)

            material_index = len(self.newGLTF.materials)
            self.newGLTF.materials.append(m)

            at = Attributes(POSITION=position_index, TEXCOORD_0=texcoord_index)
            pr = Primitive(attributes=at, material=material_index, mode=4, indices=indices_index)
            me = Mesh()
            me.primitives.append(pr)
            mesh_index = len(self.newGLTF.meshes)
            self.newGLTF.meshes.append(me)

            n = Node(mesh=mesh_index)
            self.newGLTF.nodes.append(n)

        s = Scene(nodes=list(range(len(self.newGLTF.nodes))))
        self.newGLTF.scenes.append(s)
        self.newGLTF.convert_images(ImageFormat.DATAURI)

    def fromExtendedExchangeFormat(self, e):

        for subpart in range(len(e.parts[0]['subparts'])):
            part = e.parts[0]['subparts'][subpart]
            name = 'part_' + str(subpart)

            # for subpart
            vertices = list(part['vertices'])
            if type(part['indices'][0][0]) == int:
                polygons = list(part['indices'])
            else:
                polygons = list(map(lambda x: [x[0].item(), x[1].item(), x[2].item()], part['indices']))

            if not part['texCoords'] is None:
                tex_coords = list(part['texCoords'])
            else:
                tex_coords = None
            flat_polygons = [val for sublist in polygons for val in sublist]

            vertex_bytearray = bytearray()
            for vertex in vertices:
                vertex_bytearray.extend(struct.pack('<fff', vertex[0], vertex[1], vertex[2]))
            vertex_size = len(bytes(vertex_bytearray))

            ind_bytearray = bytearray()
            for i in flat_polygons:
                ind_bytearray.extend(struct.pack('h', i))
            ind_size = len(bytes(ind_bytearray))

            tex_coords_bytearray = bytearray()
            if tex_coords is not None:
                for vt in tex_coords:
                    tex_coords_bytearray.extend(struct.pack('<ff', vt[0], vt[1]))

            data = base64.b64encode(bytes(vertex_bytearray)).decode('utf-8')
            data2 = base64.b64encode(bytes(ind_bytearray)).decode('utf-8')

            DATA_URI_HEADER = "data:application/octet-stream;base64,"

            uri = f'{DATA_URI_HEADER}{data}{data2}'
            bf = Buffer(byteLength=vertex_size + ind_size, uri=uri)
            buffer_index = len(self.newGLTF.buffers)
            self.newGLTF.buffers.append(bf)

            # buffer view #0
            bw = BufferView(target=None, byteOffset=0, byteLength=vertex_size, byteStride=12, buffer=buffer_index)
            bw_index = len(self.newGLTF.bufferViews)
            self.newGLTF.bufferViews.append(bw)

            mins = [min([vertex[i] for vertex in vertices]) for i in range(3)]
            maxs = [max([vertex[i] for vertex in vertices]) for i in range(3)]
            ac = Accessor(bufferView=bw_index, byteOffset=0, componentType=5126, count=len(vertices), max=maxs,
                          min=mins,
                          type='VEC3')
            position_index = len(self.newGLTF.accessors)
            self.newGLTF.accessors.append(ac)

            # buffer view #1

            bw2 = BufferView(target=None, byteOffset=vertex_size, byteLength=ind_size, buffer=buffer_index)
            bw2_index = len(self.newGLTF.bufferViews)
            self.newGLTF.bufferViews.append(bw2)
            maxs = [max(flat_polygons)]
            mins = [min(flat_polygons)]
            aci = Accessor(bufferView=bw2_index, byteOffset=0, componentType=5123, count=len(flat_polygons), max=maxs,
                           min=mins,
                           type='SCALAR')
            indices_index = len(self.newGLTF.accessors)
            self.newGLTF.accessors.append(aci)

            if tex_coords is not None:

                DATA_URI_HEADER = "data:application/octet-stream;base64,"
                data3 = base64.b64encode(bytes(tex_coords_bytearray)).decode('utf-8')

                uri = f'{DATA_URI_HEADER}{data3}'
                bf = Buffer(byteLength=len(bytes(tex_coords_bytearray)), uri=uri)
                buffer_index = len(self.newGLTF.buffers)
                self.newGLTF.buffers.append(bf)

                # buffer view #2
                # print('buffer view #2 -> ', vertex_size+)
                bw3 = BufferView(target=None,
                                 byteOffset=0,
                                 byteLength=len(tex_coords_bytearray),
                                 buffer=buffer_index)
                bw3_index = len(self.newGLTF.bufferViews)
                self.newGLTF.bufferViews.append(bw3)

                mins = [min([vt[i] for vt in tex_coords]) for i in range(2)]
                maxs = [max([vt[i] for vt in tex_coords]) for i in range(2)]
                ac = Accessor(bufferView=bw3_index, byteOffset=0, componentType=5126, count=len(tex_coords), max=maxs,
                              min=mins,
                              type='VEC2')
                texcoord_index = len(self.newGLTF.accessors)
                self.newGLTF.accessors.append(ac)

                imageIndex = part['imageIndex']
                imageBlob = e.images[imageIndex]['imageBlob']
                imageFileName = 'C:/temp/temp_text_' + str(subpart) + '.jpg'
                blob = BytesIO(imageBlob)
                pil_img = PILImage.open(blob)
                pil_img.save(imageFileName, format='JPEG', compression="jpeg")

                img = Image(mimeType='image/jpeg', name='tex', uri=imageFileName)
                image_index = len(self.newGLTF.images)
                self.newGLTF.images.append(img)

                texture = Texture(source=image_index)
                self.newGLTF.textures.append(texture)
                baseColorTexture = TextureInfo(index=image_index, texCoord=0)
                color = [0.8, 0.8, 0.8, 1]
                pbr = PbrMetallicRoughness(baseColorFactor=color, baseColorTexture=baseColorTexture, metallicFactor=0,
                                           roughnessFactor=1)
                m = Material(alphaCutoff=0.5, alphaMode='OPAQUE', doubleSided=False, emissiveFactor=[0, 0, 0],
                             emissiveTexture=None,
                             name=name, pbrMetallicRoughness=pbr)

            else:
                texcoord_index = None
                color = [0.8, 0.8, 0.8, 1]
                pbr = PbrMetallicRoughness(baseColorFactor=color, metallicFactor=0,
                                           roughnessFactor=1)
                m = Material(alphaCutoff=0.5, alphaMode='OPAQUE', doubleSided=False, emissiveFactor=[0, 0, 0],
                             emissiveTexture=None,
                             name=name, pbrMetallicRoughness=pbr)

            material_index = len(self.newGLTF.materials)
            self.newGLTF.materials.append(m)

            at = Attributes(POSITION=position_index, TEXCOORD_0=texcoord_index)
            pr = Primitive(attributes=at, material=material_index, mode=4, indices=indices_index)
            me = Mesh()
            me.primitives.append(pr)
            mesh_index = len(self.newGLTF.meshes)
            self.newGLTF.meshes.append(me)

            n = Node(mesh=mesh_index)
            self.newGLTF.nodes.append(n)

        s = Scene(nodes=list(range(len(self.newGLTF.nodes))))
        self.newGLTF.scenes.append(s)
        self.newGLTF.convert_images(ImageFormat.DATAURI)
