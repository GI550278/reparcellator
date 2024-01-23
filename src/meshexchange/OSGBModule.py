import copy
import os.path
import io
import shutil

from pyproj import Transformer
from numpy import array
import xml.etree.ElementTree as ET
from lxml import etree

from meshexchange.Surface.Extent import Extent
from meshexchange.Splitter import Splitter
# from bin.split_tile.Splitter import Splitter
from meshexchange.BinaryFile import BinaryFile
from meshexchange.ExchangeFormat import ExchangeFormat
from meshexchange.ExtendedExchangeFormat import ExtendedExchangeFormat
from osgblib.MatrixTransform import MatrixTransform

from osgblib.VertexBufferObject import VertexBufferObject
from osgblib.Vec3Array import Vec3Array
from osgblib.Vec2Array import Vec2Array
from osgblib.ElementBufferObject import ElementBufferObject
from osgblib.WriteHint import WriteHint
from osgblib.DrawElementsUInt import DrawElementsUInt
from osgblib.Geometry import Geometry
from osgblib.Geode import Geode
from osgblib.Group import Group
from osgblib.PagedLOD import PagedLOD
from osgblib.StateSet import StateSet
from osgblib.Material import Material
from osgblib.Texture2D import Texture2D
from osgblib.Image import Image
from osgblib.OSGBStreamWriter import OSGBStreamWriter
from osgblib.OSGBStreamReader import OSGBStreamReader
from math import sqrt
from io import BytesIO
from PIL import Image as PILImage


class OSGBModule:

    def __init__(self, version=161, **kwargs):
        self.version = version
        self.tile_buffer = kwargs['tile_buffer'] if 'tile_buffer' in kwargs else 0.005
        self.image_index = kwargs['image_index'] if 'image_index' in kwargs else 0
        self.OnCreateReference = kwargs['on_create_reference'] if 'on_create_reference' in kwargs else True
        self.destination_directory_root = kwargs['destination_directory_root'] \
            if 'destination_directory_root' in kwargs else None
        self.data_directory = kwargs['data_directory'] if 'data_directory' in kwargs else None
        self.utm_origin = kwargs['utm_origin'] if 'utm_origin' in kwargs else None
        self.range = kwargs['range'] if 'range' in kwargs else None
        self.main_extent = kwargs['main_extent'] if 'main_extent' in kwargs else None
        self.buildHeader()
        self.stateSetCache = {}

    def buildHeader(self):
        if self.version == 161:
            h = [self.version, 0, 0, 0, 4, 0, 0, 0, 1, 0, 0, 0, 48]
        elif self.version == 91:
            h = [91, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 48]
        elif self.version == 80:
            h = [80, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 48]
        else:
            raise Exception('version not supported')
        self.OSGB_HEADER = [161, 14, 145, 108, 69, 69, 251, 26, 1, 0, 0, 0] + h

    def extendedExchangeToGroupTwoRanges(self, ee, jpegQuality=None, reduce=None):
        # splitter = Splitter(ee)
        # ee_parts = splitter.split()
        grp = Group("")
        pn = 0
        for e in ee.parts:
            pn += 1
            children_number = len(e['children'])

            geode_name = "geode"
            geode = Geode(geode_name)

            e_max = [-1e99, -1e99, -1e99]
            e_min = [1e99, 1e99, 1e99]
            spn = 0
            for subpart in e['subparts']:
                spn += 1

                # geometry_name = "geometry" + str(spn)
                geometry_name = ""
                polygons = subpart['indices']
                vertices_ECEF = subpart['vertices']
                texCoords = subpart['texCoords']

                onTexture = not (subpart['imageIndex'] is None or texCoords is None)

                # todo: choose the right peleh
                transformer = Transformer.from_crs("epsg:4978", "epsg:32636")

                if not 'matrix' in subpart:
                    transform_matrix = array([1, 0, 0, 0,
                                              0, 1, 0, 0,
                                              0, 0, 1, 0,
                                              0, 0, 0, 1]).reshape((4, 4))
                else:
                    transform_matrix = array(subpart['matrix']).reshape((4, 4))

                origin = array(ee.origin)
                if self.utm_origin is None:
                    if self.isReferenceExist():
                        self.utm_origin = self.readReference()
                    else:
                        if origin[0] == 0 and origin[1] == 0 and origin[2] == 0:
                            # assuming reference is 0,0,0
                            self.utm_origin = [0, 0, 0]
                            if len(vertices_ECEF) > 0 and self.OnCreateReference:
                                vt = vertices_ECEF[0]
                                vt_arr = array(vt + [1])
                                va = list(transform_matrix.dot(vt_arr)[0:3] + origin)
                                self.utm_origin = list(transformer.transform(*va))
                        else:
                            # create reference from origin
                            self.utm_origin = list(transformer.transform(*ee.origin))
                        self.writeReference(self.utm_origin)

                vertices = []
                for vt in vertices_ECEF:
                    vt_arr = array(vt + [1])
                    va = list(transform_matrix.dot(vt_arr)[0:3] + origin)
                    utm_v = list(transformer.transform(*va))
                    v = [utm_v[0] - self.utm_origin[0], utm_v[1] - self.utm_origin[1], utm_v[2] - self.utm_origin[2]]
                    vertices.append(v)

                    for k in range(3):
                        if e_max[k] < v[k]:
                            e_max[k] = v[k]
                        if e_min[k] > v[k]:
                            e_min[k] = v[k]
                g = Geometry(geometry_name)
                ss = StateSet()
                m = Material()
                if onTexture:
                    imageDict = ee.images[subpart['imageIndex']]
                    t2d = Texture2D()
                    t2d.image = self.prepareImage(imageDict, spn, jpegQuality, reduce)

                deu = DrawElementsUInt()
                v = ElementBufferObject()
                deu.bufferObject = v
                deu.indices = polygons

                #####

                v3 = Vec3Array()
                v = VertexBufferObject()
                v3.bufferObject = v
                for vertex in vertices:
                    v3.points.append(vertex)
                ######

                vt = VertexBufferObject(v.id)
                vt.OnReference = True

                if onTexture:

                    tex = Vec2Array()
                    tex.bufferObject = vt
                    for vertex in texCoords:
                        tex.points.append(vertex)
                #####

                ss.attributeList.append(m)
                if onTexture:
                    ss.textureAttributeList.append([t2d])
                g.stateSet = ss
                g.primitiveSetList.append(deu)
                g.vecArray.append(v3)
                if onTexture:
                    g.texCoordArrayList.append(tex)

                geode.drawables.append(g)

            if children_number > 0:
                R = sqrt((e_max[0] - e_min[0]) ** 2 + (e_max[1] - e_min[1]) ** 2 + (e_max[2] - e_min[2]) ** 2) / 2.0
                userCenter = [(e_max[0] + e_min[0]) / 2.0, (e_max[1] + e_min[1]) / 2.0, (e_max[2] + e_min[2]) / 2.0, R]
                for cn in range(children_number):
                    plod = PagedLOD()
                    if cn == 0:
                        plod.children.append(geode)
                    else:
                        plod.children = [Geode()]
                    if self.range is None:
                        raise Exception('The range for PagedLOD is None')
                    plod.userCenter = userCenter
                    plod.rangeDataList = [""]
                    plod.rangeList = [[0.0, self.range]]
                    plod.rangeDataList.append(e['children'][cn])
                    plod.rangeList.append([self.range, 1e30])

                    grp.children.append(plod)
            else:
                grp.children.append(geode)

        return grp

    def extendedExchangeToGroupSplit(self, ee, jpegQuality=None, reduce=None):

        if len(ee.parts) > 1:
            raise Exception('more than one part - not supported')
        e = ee.parts[0]
        splitter = Splitter(ee)

        children_number = len(e['children']) if 'children' in e else 0

        if children_number < 2:
            if self.main_extent is None:
                return self.extendedExchangeToGroup(ee, jpegQuality, reduce)
            else:
                ex = splitter.ee_utm
                ee_extent = Extent(ex.extent[0][0], ex.extent[0][1], ex.extent[1][0], ex.extent[1][1], '32636')
                if self.main_extent.intersect(ee_extent):
                    ee_cut = splitter.cut_by_extent(self.main_extent)
                    ee_cut.parts[0]['children'] = ee.parts[0]['children']
                    return self.extendedExchangeToGroup(ee_cut, jpegQuality, reduce)
                else:
                    return self.extendedExchangeToGroup(ee, jpegQuality, reduce)

        grp = Group("")
        for k in range(len(e['children'])):
            child = e['children'][k]
            child_extent = e['children_extent'][k]
            extent = Extent.fromRad(child_extent)
            if self.main_extent is None:
                extent_utm = extent.transform('32636').buffer_procent(self.tile_buffer)
            else:
                extent_utm = extent.transform('32636').buffer_procent(self.tile_buffer).intersection(self.main_extent)

            child_ee = splitter.cut_by_extent(extent_utm)
            child_ee.parts[0]['children'] = [child]
            child_group = self.extendedExchangeToGroup(child_ee, jpegQuality, reduce)
            grp.children.append(child_group)

        return grp

    def part_to_geode(self, e, ee, jpegQuality, reduce):
        # @todo: optimize input parameters

        geode_name = "geode"
        geode = Geode(geode_name)
        e_max = [-1e99, -1e99, -1e99]
        e_min = [1e99, 1e99, 1e99]
        spn = 0
        for subpart in e['subparts']:
            spn += 1

            # geometry_name = "geometry" + str(spn)
            geometry_name = ""
            polygons = subpart['indices']
            vertices_ECEF = subpart['vertices']
            texCoords = subpart['texCoords']

            onTexture = not (subpart['imageIndex'] is None or texCoords is None)

            # todo: choose the right peleh
            transformer = Transformer.from_crs("epsg:4978", "epsg:32636")

            if not 'matrix' in subpart:
                transform_matrix = array([1, 0, 0, 0,
                                          0, 1, 0, 0,
                                          0, 0, 1, 0,
                                          0, 0, 0, 1]).reshape((4, 4))
            else:
                transform_matrix = array(subpart['matrix']).reshape((4, 4))

            origin = array(ee.origin)
            if self.utm_origin is None:
                if self.isReferenceExist():
                    self.utm_origin = self.readReference()
                else:
                    if origin[0] == 0 and origin[1] == 0 and origin[2] == 0:
                        # assuming reference is 0,0,0
                        self.utm_origin = [0, 0, 0]
                        if len(vertices_ECEF) > 0 and self.OnCreateReference:
                            vt = vertices_ECEF[0]
                            vt_arr = array(vt + [1])
                            va = list(transform_matrix.dot(vt_arr)[0:3] + origin)
                            self.utm_origin = list(transformer.transform(*va))
                    else:
                        # create reference from origin
                        self.utm_origin = list(transformer.transform(*ee.origin))
                    self.writeReference(self.utm_origin)

            vertices = []
            for vt in vertices_ECEF:
                vt_arr = array(vt + [1])
                va = list(transform_matrix.dot(vt_arr)[0:3] + origin)
                utm_v = list(transformer.transform(*va))
                v = [utm_v[0] - self.utm_origin[0], utm_v[1] - self.utm_origin[1], utm_v[2] - self.utm_origin[2]]
                vertices.append(v)

                for k in range(3):
                    if e_max[k] < v[k]:
                        e_max[k] = v[k]
                    if e_min[k] > v[k]:
                        e_min[k] = v[k]
            g = Geometry(geometry_name)
            ss = StateSet()
            m = Material()
            if onTexture:
                imageDict = ee.images[subpart['imageIndex']]
                t2d = Texture2D()
                t2d.image = self.prepareImage(imageDict, spn, jpegQuality, reduce)

            deu = DrawElementsUInt()
            v = ElementBufferObject()
            deu.bufferObject = v
            deu.indices = polygons

            #####

            v3 = Vec3Array()
            v = VertexBufferObject()
            v3.bufferObject = v
            for vertex in vertices:
                v3.points.append(vertex)
            ######

            vt = VertexBufferObject(v.id)
            vt.OnReference = True

            if onTexture:

                tex = Vec2Array()
                tex.bufferObject = vt
                for vertex in texCoords:
                    tex.points.append(vertex)
            #####

            ss.attributeList.append(m)
            if onTexture:
                ss.textureAttributeList.append([t2d])
            g.stateSet = ss
            g.primitiveSetList.append(deu)
            g.vecArray.append(v3)
            if onTexture:
                g.texCoordArrayList.append(tex)

            geode.drawables.append(g)
        return e_max, e_min, geode

    def extendedExchangeToGroup(self, ee, jpegQuality=None, reduce=None):

        grp = Group("")
        pn = 0
        for e in ee.parts:
            pn += 1
            children_number = len(e['children']) if 'children' in e else 0

            if children_number > 0:
                plod = PagedLOD()

            geode_name = "geode"
            geode = Geode(geode_name)

            e_max = [-1e99, -1e99, -1e99]
            e_min = [1e99, 1e99, 1e99]
            spn = 0
            for subpart in e['subparts']:
                spn += 1

                # geometry_name = "geometry" + str(spn)
                geometry_name = ""
                polygons = subpart['indices']
                vertices_ECEF = subpart['vertices']
                texCoords = subpart['texCoords']

                onTexture = not (subpart['imageIndex'] is None or texCoords is None)

                # todo: choose the right peleh
                transformer = Transformer.from_crs("epsg:4978", "epsg:32636")

                if not 'matrix' in subpart:
                    transform_matrix = array([1, 0, 0, 0,
                                              0, 1, 0, 0,
                                              0, 0, 1, 0,
                                              0, 0, 0, 1]).reshape((4, 4))
                else:
                    transform_matrix = array(subpart['matrix']).reshape((4, 4))

                origin = array(ee.origin)
                if self.utm_origin is None:
                    if self.isReferenceExist():
                        self.utm_origin = self.readReference()
                    else:
                        if origin[0] == 0 and origin[1] == 0 and origin[2] == 0:
                            # assuming reference is 0,0,0
                            self.utm_origin = [0, 0, 0]
                            if len(vertices_ECEF) > 0 and self.OnCreateReference:
                                vt = vertices_ECEF[0]
                                vt_arr = array(vt + [1])
                                va = list(transform_matrix.dot(vt_arr)[0:3] + origin)
                                self.utm_origin = list(transformer.transform(*va))
                        else:
                            # create reference from origin
                            self.utm_origin = list(transformer.transform(*ee.origin))
                        self.writeReference(self.utm_origin)

                vertices = []
                for vt in vertices_ECEF:
                    vt_arr = array(vt + [1])
                    va = list(transform_matrix.dot(vt_arr)[0:3] + origin)
                    utm_v = list(transformer.transform(*va))
                    v = [utm_v[0] - self.utm_origin[0], utm_v[1] - self.utm_origin[1], utm_v[2] - self.utm_origin[2]]
                    vertices.append(v)

                    for k in range(3):
                        if e_max[k] < v[k]:
                            e_max[k] = v[k]
                        if e_min[k] > v[k]:
                            e_min[k] = v[k]
                g = Geometry(geometry_name)
                ss = StateSet()
                m = Material()
                if onTexture:
                    imageDict = ee.images[subpart['imageIndex']]
                    t2d = Texture2D()
                    t2d.image = self.prepareImage(imageDict, spn, jpegQuality, reduce)

                deu = DrawElementsUInt()
                v = ElementBufferObject()
                deu.bufferObject = v
                deu.indices = polygons

                #####

                v3 = Vec3Array()
                v = VertexBufferObject()
                v3.bufferObject = v
                for vertex in vertices:
                    v3.points.append(vertex)
                ######

                vt = VertexBufferObject(v.id)
                vt.OnReference = True

                if onTexture:

                    tex = Vec2Array()
                    tex.bufferObject = vt
                    for vertex in texCoords:
                        tex.points.append(vertex)
                #####

                ss.attributeList.append(m)
                if onTexture:
                    ss.textureAttributeList.append([t2d])
                g.stateSet = ss
                g.primitiveSetList.append(deu)
                g.vecArray.append(v3)
                if onTexture:
                    g.texCoordArrayList.append(tex)

                geode.drawables.append(g)

            if children_number > 0:
                R = sqrt((e_max[0] - e_min[0]) ** 2 + (e_max[1] - e_min[1]) ** 2 + (e_max[2] - e_min[2]) ** 2) / 2.0
                userCenter = [(e_max[0] + e_min[0]) / 2.0, (e_max[1] + e_min[1]) / 2.0, (e_max[2] + e_min[2]) / 2.0, R]
                plod.children.append(geode)
                plod.userCenter = userCenter

                plod.rangeDataList = [""]
                plod.rangeList = [[0.0, self.range]]
                plod.priorityList = [[1.0, 0.0]]
                for cn in range(children_number):
                    plod.rangeDataList.append(e['children'][cn])
                    plod.rangeList.append([self.range, 1e30])
                    plod.priorityList.append([1.0, 0.0])

                grp.children.append(plod)
            else:
                grp.children.append(geode)

        return grp

    def prepareImage(self, imageDict, index, jpegQuality, reduce):

        imageBlob = imageDict['imageBlob']
        imageFile = imageDict['imageFile'] if 'imageFile' in imageDict else f'image_{index}.jpg'
        imageSize = imageDict['imageSize'] if 'imageSize' in imageDict else None
        imageShape = [1, 0, 0] if imageSize is None else imageSize + [1]

        srcImagePath = imageDict['srcImagePath'] if 'srcImagePath' in imageDict else ''
        if srcImagePath is None:
            srcImagePath = ''

        writeHint = imageDict['writeHint']
        if isinstance(writeHint, list):
            if not len(writeHint) == 2:
                raise Exception('bad writeHint' + str(writeHint))
        else:
            writeHint = [imageDict['writeHint'], 0]

        sourceImageType = writeHint[0]
        if sourceImageType == 0:
            if len(imageBlob) > 0:  # and len(srcImagePath) == 0:
                sourceImageType = WriteHint.STORE_INLINE.value
            elif len(imageBlob) == 0:
                sourceImageType = WriteHint.EXTERNAL_FILE.value
            else:
                raise Exception('Cannot determine source image type')

        destinationImageType = writeHint[1]
        if destinationImageType == 0:
            destinationImageType = 1

        # there are 2x2 variations

        if sourceImageType == WriteHint.EXTERNAL_FILE.value and destinationImageType == WriteHint.EXTERNAL_FILE.value:
            imagePath = imageDict['imagePath']
            imag = Image(imageFile, imageBlob)
            imag.shape = imageShape

            if jpegQuality is None:
                shutil.copyfile(srcImagePath, imagePath)
            else:
                img = PILImage.open(srcImagePath)
                img.save(imagePath, format='jpeg', quality=jpegQuality)
                imag.shape = list(img.size) + [1]
        elif sourceImageType == WriteHint.EXTERNAL_FILE.value and destinationImageType == WriteHint.STORE_INLINE.value:
            img = PILImage.open(srcImagePath)
            if reduce is not None:
                img = img.resize((int(img.size[0] * reduce), int(img.size[1] * reduce)))

            imageBytesIO = io.BytesIO()
            img.save(imageBytesIO, format='JPEG', compression="jpeg")
            img = PILImage.open(imageBytesIO)
            imag = Image(imageFile, imageBytesIO.getbuffer().tobytes())

            imag.shape = list(img.size) + [1]

        elif sourceImageType == WriteHint.STORE_INLINE.value and destinationImageType == WriteHint.EXTERNAL_FILE.value:
            imagePath = imageDict['imagePath']
            imag = Image(imageFile, b'')

            if (b'JFIF' in imageBlob[0:20]):
                blob = BytesIO(imageBlob)
                img = PILImage.open(blob)
                imag.shape = list(img.size) + [1]
            else:
                img = PILImage.frombytes("RGB", imageSize, bytes(imageBlob))
                imag.shape = imageShape

            if jpegQuality is None:
                if img.size[0] < 256:
                    img = img.resize((256, 256))
                    imag.shape = list(img.size) + [1]

                img.save(imagePath, format='jpeg')
            else:
                img.save(imagePath, format='jpeg', quality=jpegQuality)
        elif sourceImageType == WriteHint.STORE_INLINE.value and destinationImageType == WriteHint.STORE_INLINE.value:
            if (b'JFIF' in imageBlob[0:20]):
                blob = BytesIO(imageBlob)
                img = PILImage.open(blob)
            else:
                img = PILImage.frombytes("RGB", imageSize, bytes(imageBlob))

            if reduce is not None:
                img = img.resize((int(img.size[0] * reduce), int(img.size[1] * reduce)))

            imageBytesIO = io.BytesIO()
            img.save(imageBytesIO, format='JPEG', compression="jpeg")
            img = PILImage.open(imageBytesIO)
            imag = Image(imageFile, imageBytesIO.getbuffer().tobytes())
            imag.shape = list(img.size) + [1]

            # todo: add support to webp
            # if img_.format == 'WEBP':
            #     imageBytesIO = io.BytesIO()
            #     img_.save(imageBytesIO, format='JPEG', compression="jpeg")
            #     img = PILImage.open(imageBytesIO)
            #     imag = Image(imageFile, imageBytesIO.getbuffer().tobytes())
            # else:
            #     img = img_

        imag.writeHint = writeHint

        return imag

    def readReference(self):
        return self.readMetadataFile(self.destination_directory_root + '/metadata.xml')
        # with open(self.destination_directory_root + '/origin.dat', 'rb') as file:
        #     return pickle.load(file)

    def writeReference(self, utm_origin):
        # with open(self.destination_directory_root + '/origin.dat', 'wb') as file:
        #     pickle.dump(utm_origin, file)
        print('\nUTM36 reference point:', utm_origin)
        print('Writing metadata...')
        self.writeMetadataFile(self.destination_directory_root + '/metadata.xml')

    def isReferenceExist(self):
        return os.path.exists(self.destination_directory_root + '/metadata.xml')

    def exchangeToGroup(self, e, additionalData=[{}]):
        polygons = e.indices
        vertices = e.vertices
        texCoords = e.texCoords

        if additionalData[0] == {}:
            subTileName = "unknown.osgb"
            # find center
            e_max = [-1e99, -1e99, -1e99]
            e_min = [1e99, 1e99, 1e99]
            for v in e.vertices:
                for k in range(3):
                    if e_max[k] < v[k]:
                        e_max[k] = v[k]
                    if e_min[k] > v[k]:
                        e_min[k] = v[k]

            R = sqrt((e_max[0] - e_min[0]) ** 2 + (e_max[1] - e_min[1]) ** 2 + (e_max[2] - e_min[2]) ** 2) / 2.0
            userCenter = [(e_max[0] + e_min[0]) / 2.0, (e_max[1] + e_min[1]) / 2.0, (e_max[2] + e_min[2]) / 2.0, R]

            if len(e.imageBlob) == 0:
                imageShape = [1, 0, 0]
                writeHint = [2, 2]
            else:
                blob = BytesIO(e.imageBlob)
                img = PILImage.open(blob)
                imageShape = list(img.size) + [1]
                writeHint = [0, 1]

            additionalData = [{'geode_name': e.subTileName,
                               'rangeDataList': ["", e.subTileName],
                               'rangeList': [[0.0, R], [R, 1e+30]],
                               'userCenter': userCenter,
                               'imageShape': imageShape,
                               'writeHint': writeHint
                               }]

        # this is additional data that is not in exchange format
        geode_name = additionalData[0]['geode_name'] if 'geode_name' in additionalData[0] else "unknown.osgb"
        geometry_name = additionalData[0]['geometry_name'] if 'geometry_name' in additionalData[0] else ""
        rangeDataList = additionalData[0]['rangeDataList'] if 'rangeDataList' in additionalData[0] else ["",
                                                                                                         "unknown.osgb"]
        rangeList = additionalData[0]['rangeList'] \
            if 'rangeList' in additionalData[0] else [[0.0, 200.0],
                                                      [200.2, 1.0e+30]]
        userCenter = additionalData[0]['userCenter'] \
            if 'userCenter' in additionalData[0] else [2017.0,
                                                       985.52,
                                                       226.97,
                                                       198.48]
        imageShape = additionalData[0]['imageShape'] \
            if 'imageShape' in additionalData[0] else [1, 0, 0]

        writeHint = additionalData[0]['writeHint'] \
            if 'writeHint' in additionalData[0] else [0, 1]

        grp = Group("", 1)
        plod = PagedLOD(2)

        plod.rangeDataList = rangeDataList
        plod.rangeList = rangeList
        plod.userCenter = userCenter

        geode = Geode(geode_name, 3)
        g = Geometry(geometry_name, 4)
        ss = StateSet(5)
        m = Material(6)
        t2d = Texture2D(7)
        img = Image(e.imageFile, e.imageBlob, 8)
        img.shape = imageShape
        img.writeHint = writeHint
        t2d.image = img

        v = ElementBufferObject(10)

        deu = DrawElementsUInt(9)
        deu.bufferObject = v
        deu.indices = polygons

        #####
        v = VertexBufferObject(12)

        v3 = Vec3Array(11)
        v3.bufferObject = v
        for vertex in vertices:
            v3.points.append(vertex)
        ######

        vt = VertexBufferObject(12)
        vt.OnReference = True

        tex = Vec2Array(13)
        tex.bufferObject = vt
        for vertex in texCoords:
            tex.points.append(vertex)
        #####

        ss.attributeList.append(m)
        ss.textureAttributeList.append([t2d])
        g.stateSet = ss
        g.primitiveSetList.append(deu)
        g.vecArray.append(v3)
        g.texCoordArrayList.append(tex)

        geode.drawables.append(g)
        plod.children.append(geode)
        grp.children.append(plod)
        return grp

    def groupToExtendedExchange(self, group, dstImageDir='', srcImageDir='',
                                utm_origin=None, imageFile=None, writeHint=None):
        self.image_index = 0

        # x1, y1, h = 389766.003191636, 5817577.38103416, 37.8899993896484
        if utm_origin is None:
            utm_origin = [0.0, 0.0, 0.0]
        parts = []
        images = []
        transformer = Transformer.from_crs("epsg:32636", "epsg:4978")

        ecef_origin = list(transformer.transform(*utm_origin))

        if isinstance(group, Group):
            for pageLod in group.children:
                if isinstance(pageLod, PagedLOD):
                    part = self.extractPartFromPagedLOD(images, pageLod, utm_origin, ecef_origin,
                                                        dstImageDir,
                                                        srcImageDir, imageFile, writeHint)
                elif isinstance(pageLod, Geode):
                    part = {'subparts': [], 'children': []}
                    self.extractSubpartFromGeode(pageLod, images, part, utm_origin, ecef_origin,
                                                 dstImageDir,
                                                 srcImageDir, imageFile, writeHint)
                else:
                    raise Exception('group children object not supported', pageLod.__class__.__name__)
                parts.append(part)
        elif isinstance(group, Geode):
            part = {'subparts': [], 'children': []}
            self.extractSubpartFromGeode(group, images, part, utm_origin, ecef_origin, dstImageDir,
                                         srcImageDir, imageFile, writeHint)
            parts.append(part)
        else:
            raise Exception('object not supported', group.__class__.__name__)

        return ExtendedExchangeFormat(parts=parts, images=images, origin=ecef_origin)

    def extractPartFromPagedLOD(self, images, pageLod, utm_origin, ecef_origin, dstImageDir='',
                                srcImageDir='', imageFile=None, writeHint=None):
        part = {'subparts': [], 'children': []}
        for k in range(1, len(pageLod.rangeDataList)):
            part['children'].append(pageLod.rangeDataList[k])

        for geode in pageLod.children:
            self.extractSubpartFromGeode(geode, images, part, utm_origin, ecef_origin, dstImageDir,
                                         srcImageDir, imageFile, writeHint)
        return part

    def extractSubpartFromGeode(self, geode, images, part, utm_origin, ecef_origin, dstImageDir='',
                                srcImageDir='', imageFile=None, writeHint=None):
        for geometry in geode.drawables:
            vertices_UTM = geometry.vecArray[0].points
            # todo: choose the right peleh
            transformer = Transformer.from_crs("epsg:32636", "epsg:4978")

            vertices = []
            for vt in vertices_UTM:
                utm_v = [vt[0] + utm_origin[0], vt[1] + utm_origin[1], vt[2] + utm_origin[2]]
                ecef_v = list(transformer.transform(*utm_v))
                v = [ecef_v[0] - ecef_origin[0], ecef_v[1] - ecef_origin[1], ecef_v[2] - ecef_origin[2]]
                vertices.append(v)

            indices = geometry.primitiveSetList[0].indices

            if geometry.stateSet.OnReference:
                geometry.stateSet = self.stateSetCache[geometry.stateSet.id]
            else:
                self.stateSetCache[geometry.stateSet.id] = geometry.stateSet

            image = geometry.stateSet.textureAttributeList[0][0].image

            image_filename = image.filename if imageFile is None else imageFile.replace('.jpg',
                                                                                        f'_{self.image_index}.jpg')
            self.image_index += 1

            img = {'imageBlob': image.imageBuffer, 'imageFile': image_filename, 'imageSize': image.shape[0:2],
                   'writeHint': writeHint, 'imagePath': dstImageDir + '/' + image_filename,
                   'srcImagePath': srcImageDir + '/' + image_filename}

            if self.isFlipRequired(img):
                texCoords = []
                for tx in geometry.texCoordArrayList[0].points:
                    u, v = tx[0], 1 - tx[1]
                    texCoords.append([u, v])
            else:
                texCoords = geometry.texCoordArrayList[0].points

            imageIndex = len(images)
            images.append(img)
            subpart = {'indices': indices, 'vertices': vertices, 'texCoords': texCoords, 'imageIndex': imageIndex,
                       'matrix': [1, 0, 0, 0,
                                  0, 1, 0, 0,
                                  0, 0, 1, 0,
                                  0, 0, 0, 1]}
            part['subparts'].append(subpart)

    def groupToExchange(self, group):
        e = ExchangeFormat()
        e.indices = group.children[0].children[0].drawables[0].primitiveSetList[0].indices
        e.vertices = group.children[0].children[0].drawables[0].vecArray[0].points
        e.texCoords = group.children[0].children[0].drawables[0].texCoordArrayList[0].points
        e.imageBlob = group.children[0].children[0].drawables[0].stateSet.textureAttributeList[0][
            0].image.imageBuffer
        e.imageFile = group.children[0].children[0].drawables[0].stateSet.textureAttributeList[0][0].image.filename
        return e

    def groupToFile(self, group, fileName):
        w = OSGBStreamWriter(bytearray(), self.version)
        w.clear()
        w.writeBytes(self.OSGB_HEADER)
        w.writeObject(group)
        bf = BinaryFile(file_name=fileName)
        bf.write_all(w.payload)

    def groupToByteArray(self, group):
        w = OSGBStreamWriter()
        w.clear()
        w.writeBytes(self.OSGB_HEADER)
        w.writeObject(group)
        return w.payload

    def byteArrayToGroup(self, payload):
        p = OSGBStreamReader(payload)
        p.verifyBytes(self.OSGB_HEADER)
        return p.readObject()

    def byteArrayToFile(self, payload, fileName):
        bf = BinaryFile(file_name=fileName)
        bf.write_all(payload)

    def fileToByteArray(self, fileName):
        bf = BinaryFile(file_name=fileName)
        return bf.read_all()

    def fileToGroup(self, fileName):
        bf = BinaryFile(file_name=fileName)
        complete = bf.read_all()
        s = OSGBStreamReader(complete, self.version)
        # s.report(80)
        # print(self.OSGB_HEADER)
        s.verifyBytes(self.OSGB_HEADER)
        if self.version == 161:
            return s.readObject()
        if self.version == 91:
            return s.readObjectNoGut()
        if self.version == 80:
            return s.readObjectNoGut()
        return None

    def getChildrenNames(self, group):
        if not (isinstance(group, Group) or isinstance(group, MatrixTransform)):
            return []

        children = []
        for child in group.children:
            if isinstance(child, PagedLOD):
                for childName in child.rangeDataList:
                    if len(childName) > 0:
                        children.append(childName)
        return children

    def cleanChildren(self, group):
        if not isinstance(group, Group):
            return
        geodes = []
        for child in group.children:
            if isinstance(child, PagedLOD):
                for grandChild in child.children:
                    if isinstance(grandChild, Geode):
                        geodes.append(grandChild)
        group.children = geodes

    def writeMetadataFile(self, fileName):
        modelMetadata = ET.Element('ModelMetadata')
        modelMetadata.attrib['version'] = '1'
        srs = ET.Element('SRS')
        srs.text = "EPSG:32636+5773"
        modelMetadata.append(ET.Comment("Spatial Reference System"))
        modelMetadata.append(srs)

        srsOrigin = ET.Element('SRSOrigin')
        srsOrigin.text = ",".join(["%.4f" % x for x in self.utm_origin])
        modelMetadata.append(ET.Comment("Origin in Spatial Reference System"))
        modelMetadata.append(srsOrigin)
        texture = ET.Element('Texture')
        colorSource = ET.Element('ColorSource')
        colorSource.text = "Visible"
        texture.append(colorSource)
        modelMetadata.append(texture)

        root = etree.fromstring(ET.tostring(modelMetadata, encoding='utf8', method='xml'))

        etree.indent(root, space="\t")
        xml_object = etree.tostring(root,
                                    pretty_print=True,
                                    xml_declaration=True,
                                    encoding='utf-8')

        with open(fileName, "wb") as writter:
            writter.write(xml_object)

    def replaceMissingTextures(self, group):
        group2 = copy.copy(group)
        for child in group2.children:
            if isinstance(child, PagedLOD):
                for child2 in child.children:
                    for geometry in child2.drawables:
                        if len(geometry.texCoordArrayList) == 0:
                            dummyTexture = Vec2Array()
                            n = len(geometry.vecArray[0].points)
                            for k in range(n):
                                dummyTexture.points.append([0, 1])
                            geometry.stateSet.textureAttributeList.append([])
                            geometry.texCoordArrayList.append(dummyTexture)
            elif isinstance(child, Geode):
                for geometry in child.drawables:
                    if len(geometry.texCoordArrayList) == 0:
                        dummyTexture = Vec2Array()
                        n = len(geometry.vecArray[0].points)
                        for k in range(n):
                            dummyTexture.points.append([0, 1])
                        geometry.stateSet.textureAttributeList.append([])
                        geometry.texCoordArrayList.append(dummyTexture)
        #
        # for child in group2.children:
        #     if isinstance(child, Geode):
        #         geom = child.drawables[0]
        #         # geom.stateSet.textureAttributeList = []
        #         tex2d = geom.stateSet.textureAttributeList[0][0]
        #         image = tex2d.image
        #         image.filename = 'b.jpg'
        #         image.shape = [200,200, 1]
        #
        #         tex2d.image = image
        #         geom.stateSet.textureAttributeList[0] = [tex2d]
        #         child.drawables = [geom]

        return group2

    def readMetadataFile(self, fileName):
        root = etree.parse(fileName)
        records = root.xpath('/ModelMetadata/SRSOrigin')
        return list(map(float, records[0].text.split(',')))

    def isFlipRequired(self, imageDict):
        imageBlob = imageDict['imageBlob']
        if len(imageBlob) > 0:
            return True
        elif len(imageBlob) == 0:
            return False
