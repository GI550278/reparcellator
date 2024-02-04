import copy

from pyproj import Transformer
from shapely import MultiPoint, convex_hull


class ExtendedExchangeFormat:

    def __init__(self, **kwargs):
        self.parts = kwargs['parts'] if 'parts' in kwargs \
            else [{'subparts': [{'indices': [], 'vertices': [], 'texCoords': [], 'imageIndex': 0,
                                 'matrix': [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]}], 'children': []}]
        self.images = kwargs['images'] if 'images' in kwargs else \
            [{'imageBlob': bytearray(), 'imageFile': "", "imageSize": [0, 0], 'writeHint': 0}]
        self.origin = kwargs['origin'] if 'origin' in kwargs else [0, 0, 0]
        self.extent = None

    def add(self, e):
        p0 = e.parts[0]['subparts'][0]
        x = len(self.images)
        if not p0['imageIndex'] is None:
            img = e.images[p0['imageIndex']]
            self.parts[0]['subparts'].append({'indices': p0['indices'], 'vertices': p0['vertices'],
                                              'texCoords': p0['texCoords'], 'imageIndex': p0['imageIndex'] + x})
            self.images.append({'imageBlob': img['imageBlob'], 'imageFile': img['imageFile']})
        else:
            self.parts.append({'indices': p0['indices'], 'vertices': p0['vertices'],
                               'texCoords': p0['texCoords'], 'imageIndex': None})

    def project(self, fromSrc="epsg:4978", toSrc="epsg:32636", dst_origin=None):
        new_ee = ExtendedExchangeFormat()
        new_ee.images = copy.deepcopy(self.images)
        new_ee.parts = []

        transformer = Transformer.from_crs(fromSrc, toSrc)

        if dst_origin is None:
            dst_origin = [0, 0, 0]
        new_ee.origin = dst_origin
        utm_origin = dst_origin

        e_max = [-1e99, -1e99, -1e99]
        e_min = [1e99, 1e99, 1e99]

        for part in self.parts:
            new_part = {'subparts': []}
            for subpart in part['subparts']:
                new_subpart = {}
                for key in subpart.keys():
                    if not key == 'vertices':
                        new_subpart[key] = copy.deepcopy(subpart[key])

                vertices_ECEF = subpart['vertices']
                origin = self.origin

                vertices = []
                for vt in vertices_ECEF:
                    va = [vt[0] + origin[0], vt[1] + origin[1], vt[2] + origin[2]]
                    utm_v = list(transformer.transform(*va))
                    v = [utm_v[0] - utm_origin[0], utm_v[1] - utm_origin[1], utm_v[2] - utm_origin[2]]
                    vertices.append(v)

                    for k in range(3):
                        if e_max[k] < v[k]:
                            e_max[k] = v[k]
                        if e_min[k] > v[k]:
                            e_min[k] = v[k]

                new_subpart['vertices'] = vertices
                new_part['subparts'].append(new_subpart)
            new_ee.parts.append(new_part)
        new_ee.extent = [e_min, e_max]
        return new_ee

    def calculateExtent(self):
        e_max = [-1e99, -1e99, -1e99]
        e_min = [1e99, 1e99, 1e99]

        for part in self.parts:
            for subpart in part['subparts']:
                vertices_ECEF = subpart['vertices']
                origin = self.origin
                for vt in vertices_ECEF:
                    v = [vt[0] + origin[0], vt[1] + origin[1], vt[2] + origin[2]]
                    for k in range(3):
                        if e_max[k] < v[k]:
                            e_max[k] = v[k]
                        if e_min[k] > v[k]:
                            e_min[k] = v[k]

        self.extent = [e_min, e_max]
        return self.extent

    def simple_convex_hull(self):
        """
        2d convex hull
        warning this method ignores z coordinates
        """
        all_vertices = []
        for part in self.parts:
            for subpart in part['subparts']:
                all_vertices.extend([[x[0],x[1]] for x in subpart['vertices']])

        return convex_hull(MultiPoint(all_vertices))

    def calculateNumberOfVertices(self):
        count = 0
        for part in self.parts:
            if 'subparts' in part:
                for subpart in part['subparts']:
                    if 'vertices' in subpart:
                        count += len(subpart['vertices'])
        return count

    def getExtent(self):
        if self.extent is None:
            self.calculateExtent()
        return self.extent

    def getCenter(self):
        if self.extent is None:
            self.calculateExtent()

        center = [0, 0, 0]
        for k in range(3):
            center[k] = (self.extent[0][k] + self.extent[1][k]) / 2

        return center
