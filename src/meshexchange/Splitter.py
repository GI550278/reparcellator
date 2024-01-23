import copy
import math
import sys

from numpy import array, cross, dot
from numpy.linalg import inv, det, norm
from scipy.spatial import Delaunay
from shapely import box, normalize, Polygon, intersection

from meshexchange.SimplePolygon import SimplePolygon
from meshexchange.Surface.Extent import Extent
from meshexchange.Surface.Plane import Plane
from meshexchange.Surface.Triangle import Triangle
from meshexchange.ExtendedExchangeFormat import ExtendedExchangeFormat


class Splitter:
    def __init__(self, ee):
        self.ee = ee
        self.ee_utm = ee.project()
        self.extent = self.ee_utm.getExtent()

    @staticmethod
    def lineIntersect(p1, p2, q1, q2):
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]

        if abs(dx) + abs(dy) < 1e-5:
            return None, None

        A = array([[dx, -q1[0] + q2[0]],
                   [dy, -q1[1] + q2[1]]])

        # v1 = A.transpose()[0]
        # v2 = A.transpose()[1]
        # v1 = v1/norm(v1)
        # v2 = v2/norm(v2)
        # c = v1.dot(v2)
        # d = A.transpose().dot(A)
        b = array([[-p2[0] + q2[0]],
                   [-p2[1] + q2[1]]])

        # d = abs(det(A))
        # print('det:', d)

        if abs(det(A)) < 1e-12:
            return None, None

        res = inv(A).dot(b)

        t = res[0, 0]
        k = res[1, 0]
        # print(f't={t},k={k}')
        e = 1e-5
        if -e <= t <= 1 + e and -e <= k <= 1 + e:
            return [t * p1[0] + (1 - t) * p2[0], t * p1[1] + (1 - t) * p2[1], t * p1[2] + (1 - t) * p2[2]], t
        else:
            return None, None

    def calcTrianglePlane3D(self, vertices):
        p0 = array(vertices[0])
        p1 = array(vertices[1])
        p2 = array(vertices[2])
        v1 = p1 - p0
        v2 = p2 - p0
        n = cross(v1, v2)
        nn = norm(n)
        n = n / nn
        D = -dot(n, p0)[0]
        return Plane(n, D)

    def cut_triangle_old(self, extent, vertices_filtered, vertices_source, tex_coords_filtered, tex_coords_source,
                         tr, tr_index):
        """
        This method cuts the given triangle and returns array of triangles
            and updates vertices_filtered and tex_coords_filtered lists

        :param extent: the cutting extent
        :param vertices_filtered: the vertices in the cut area
        :param vertices_source:  the source vertices
        :param tex_coords_filtered: the tex coords in the cut area
        :param tex_coords_source: the source tex coords
        :param tr: the triangle indices of the source vertices
        :param tr_index: the triangle indices of the filtered vertices
        :return: array of triangles

        """
        tex = [tex_coords_source[tr[0]], tex_coords_source[tr[1]], tex_coords_source[tr[2]]]
        source_triangle_coords = [vertices_source[tr[0]], vertices_source[tr[1]], vertices_source[tr[2]]]
        start_index = len(vertices_filtered)  # = len(tex_coords_filtered)

        start_k = self.first_point_inside(extent, source_triangle_coords)
        if start_k is None:
            return []

        try:
            last_intersect = None
            new_tex_coords = []
            new_pol = []
            n = len(source_triangle_coords)  # =3
            for k in [x % n for x in range(start_k, start_k + n)]:
                p1 = source_triangle_coords[k]
                p2 = source_triangle_coords[(k + 1) % n]

                if extent.isIn(p1[0], p1[1]):
                    new_pol.append(tr_index[k])
                pol = extent.asPolygon()
                intersectPoint = None
                intersectTexCoords = None
                for t in range(4):
                    q1 = pol[t]
                    q2 = pol[(t + 1) % 4]
                    try:
                        a, t = Splitter.lineIntersect(p1, p2, q1, q2)
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                    if a is not None:
                        intersectPoint = a
                        # look for points to snap
                        for k2, pol_index in enumerate(new_pol):
                            pnt = vertices_filtered[pol_index]
                            l = (pnt[0] - a[0]) ** 2 + (pnt[1] - a[1]) ** 2 + (pnt[2] - a[2]) ** 2
                            if l < 1e-5:
                                intersectPoint = None
                                # new_pol.append(tr_index[k2])
                                break
                        if intersectPoint is not None:
                            tc1 = tex[k]
                            tc2 = tex[(k + 1) % n]
                            intersectTexCoords = [t * tc1[0] + (1 - t) * tc2[0],
                                                  t * tc1[1] + (1 - t) * tc2[1]]

                            break
                if intersectPoint is not None:
                    new_pol.append(start_index)
                    start_index += 1

                    vertices_filtered.append(intersectPoint)
                    new_tex_coords.append(intersectTexCoords)

                    if last_intersect is not None:
                        e = 1e-5
                        if abs(last_intersect[0] - intersectPoint[0]) < e or abs(
                                last_intersect[1] - intersectPoint[1]) < e:
                            pass
                        else:
                            corner = [None, None]
                            # close_to_x_min = min(abs(extent.x_min - intersectPoint[0]),
                            #                      abs(extent.x_min - last_intersect[0]))
                            # close_to_x_max = min(abs(extent.x_max - intersectPoint[0]),
                            #                      abs(extent.x_max - last_intersect[0]))
                            # if close_to_x_min < close_to_x_max:
                            #     corner[0] = extent.x_min
                            # else:
                            #     corner[0] = extent.x_max
                            #
                            # close_to_y_min = min(abs(extent.y_min - intersectPoint[0]),
                            #                      abs(extent.y_min - last_intersect[0]))
                            # close_to_y_max = min(abs(extent.y_max - intersectPoint[0]),
                            #                      abs(extent.y_max - last_intersect[0]))
                            # if close_to_y_min < close_to_y_max:
                            #     corner[1] = extent.y_min
                            # else:
                            #     corner[1] = extent.y_max

                            if abs(extent.x_min - intersectPoint[0]) < e or abs(extent.x_min - last_intersect[0]) < e:
                                corner[0] = extent.x_min
                            if abs(extent.x_max - intersectPoint[0]) < e or abs(extent.x_max - last_intersect[0]) < e:
                                corner[0] = extent.x_max
                            if abs(extent.y_min - intersectPoint[1]) < e or abs(extent.y_min - last_intersect[1]) < e:
                                corner[1] = extent.y_min
                            if abs(extent.y_max - intersectPoint[1]) < e or abs(extent.y_max - last_intersect[1]) < e:
                                corner[1] = extent.y_max

                            if corner[0] is None or corner[1] is None:
                                print('failed to cut triangle')
                                return []

                            new_pol.append(start_index)
                            start_index += 1
                            plane = self.calcTrianglePlane3D(source_triangle_coords)
                            z = plane.spot(*corner)
                            vertices_filtered.append(corner + [z])
                            triangle = Triangle(source_triangle_coords)
                            lam = triangle.barycentric(corner)
                            triangle_tex = Triangle(tex)
                            corner_tex = triangle_tex.cartesian(lam)
                            new_tex_coords.append(corner_tex)

                            # print(last_intersect, intersectPoint, corner)
                        last_intersect = None
                    else:
                        last_intersect = intersectPoint

            tex_coords_filtered.extend(new_tex_coords)
            if len(new_pol) == 3:
                return [new_pol]
            if len(new_pol) < 3:
                return []
            return self.tessellate_polygon(new_pol, vertices_filtered)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print('cut triangle error', e)
            return []

    def cut_triangle_by_polygon(self, cut_polygon, vertices_filtered, vertices_source, tex_coords_filtered, tex_coords_source,
                     tr, tr_index):
        """
        This method cuts the given triangle and returns array of triangles
            and updates vertices_filtered and tex_coords_filtered lists

        :param cut_polygon: the cutting polygon
        :param vertices_filtered: the vertices in the cut area
        :param vertices_source:  the source vertices
        :param tex_coords_filtered: the tex coords in the cut area
        :param tex_coords_source: the source tex coords
        :param tr: the triangle indices of the source vertices
        :param tr_index: the triangle indices of the filtered vertices
        :return: array of triangles
        """
        tex = [tex_coords_source[tr[0]], tex_coords_source[tr[1]], tex_coords_source[tr[2]]]
        source_triangle_coords = [vertices_source[tr[0]], vertices_source[tr[1]], vertices_source[tr[2]]]
        start_index = len(vertices_filtered)
        source_triangle_polygon = Polygon(source_triangle_coords)
        if source_triangle_polygon.area < 1e-4:
            # @todo:
            #   1. find line in polygon that intersected by the triangle
            #   2. build vertical wall from the line
            #   3. translate the triangle to wall local coords
            #   4. intersect traingle in local coords
            #   5. return triangle to original coords
            print(source_triangle_coords)
            print(cut_polygon.coords())
            pass

        else:
            polygon = normalize(intersection(cut_polygon.polygon, source_triangle_polygon))

        polygon_index = []
        for p in polygon.exterior.coords:
            point_index = None
            for q_index, q in enumerate(source_triangle_polygon.exterior.coords):
                if abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2]) < 1e-5:
                    point_index = tr_index[q_index]
                    break
            if point_index is None:
                triangle = Triangle(source_triangle_coords)
                lam = triangle.barycentric(p)
                triangle_tex = Triangle(tex)
                p_tex = triangle_tex.cartesian(lam)
                tex_coords_filtered.append(p_tex)
                vertices_filtered.append(list(p))
                point_index = start_index
                start_index += 1
            polygon_index.append(point_index)

        if len(polygon_index) == 3:
            return [polygon_index]
        if len(polygon_index) < 3:
            return []
        return self.tessellate_polygon(polygon_index, vertices_filtered)

    def cut_triangle(self, extent, vertices_filtered, vertices_source, tex_coords_filtered, tex_coords_source,
                     tr, tr_index):
        """
        This method cuts the given triangle and returns array of triangles
            and updates vertices_filtered and tex_coords_filtered lists

        :param extent: the cutting extent
        :param vertices_filtered: the vertices in the cut area
        :param vertices_source:  the source vertices
        :param tex_coords_filtered: the tex coords in the cut area
        :param tex_coords_source: the source tex coords
        :param tr: the triangle indices of the source vertices
        :param tr_index: the triangle indices of the filtered vertices
        :return: array of triangles
        """
        tex = [tex_coords_source[tr[0]], tex_coords_source[tr[1]], tex_coords_source[tr[2]]]
        source_triangle_coords = [vertices_source[tr[0]], vertices_source[tr[1]], vertices_source[tr[2]]]
        start_index = len(vertices_filtered)
        extent_box = box(*extent.asArray())
        source_triangle_polygon = Polygon(source_triangle_coords)
        if source_triangle_polygon.area < 1e-4:
            z_min = -20000
            z_max = 20000
            flipped_zy_source_polygon = Polygon(map(lambda x: (x[0], x[2], x[1]), source_triangle_coords))
            flipped_zx_source_polygon = Polygon(map(lambda x: (x[2], x[1], x[0]), source_triangle_coords))
            if flipped_zy_source_polygon.area < 1e-4 and flipped_zx_source_polygon.area < 1e-4:
                return []

            if flipped_zy_source_polygon.area > flipped_zx_source_polygon.area:
                flipped_box = box(extent.x_min, z_min, extent.x_max, z_max)
                flipped_polygon = normalize(intersection(flipped_box, flipped_zy_source_polygon))
                polygon = Polygon(map(lambda x: (x[0], x[2], x[1]), flipped_polygon.exterior.coords))
            else:
                flipped_box = box(z_min, extent.y_min, z_max, extent.y_max)
                flipped_polygon = normalize(intersection(flipped_box, flipped_zx_source_polygon))
                polygon = Polygon(map(lambda x: (x[2], x[1], x[0]), flipped_polygon.exterior.coords))
        else:
            polygon = normalize(intersection(extent_box, source_triangle_polygon))

        polygon_index = []
        for p in polygon.exterior.coords:
            point_index = None
            for q_index, q in enumerate(source_triangle_polygon.exterior.coords):
                if abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2]) < 1e-5:
                    point_index = tr_index[q_index]
                    break
            if point_index is None:
                triangle = Triangle(source_triangle_coords)
                lam = triangle.barycentric(p)
                triangle_tex = Triangle(tex)
                p_tex = triangle_tex.cartesian(lam)
                tex_coords_filtered.append(p_tex)
                vertices_filtered.append(list(p))
                point_index = start_index
                start_index += 1
            polygon_index.append(point_index)

        if len(polygon_index) == 3:
            return [polygon_index]
        if len(polygon_index) < 3:
            return []
        return self.tessellate_polygon(polygon_index, vertices_filtered)

    def tessellate_polygon(self, pol, vertices):
        filtered_pol = []
        for pol_index in pol:
            pnt = vertices[pol_index]
            to_filter = False
            for fpol_index in filtered_pol:
                fpnt = vertices[fpol_index]
                l = math.sqrt((pnt[0] - fpnt[0]) ** 2 + (pnt[1] - fpnt[1]) ** 2 + (pnt[2] - fpnt[2]) ** 2)
                if l < 1e-4:
                    to_filter = True
                    break
            if not to_filter:
                filtered_pol.append(pol_index)

        if len(filtered_pol) < 3:
            print('error')
            print('bad triangle after cutting')
            return []
            # raise Exception('bad triangle after cutting')

        points = []
        for k in filtered_pol:
            points.append(vertices[k][:2])
        try:
            tri = Delaunay(points)
            triangles = []
            for triangle in tri.simplices:
                triangles.append([filtered_pol[triangle[0]], filtered_pol[triangle[1]], filtered_pol[triangle[2]]])
            return triangles
        except:
            # Delaunay may fail if the polygon is vertical
            trs = []
            while len(filtered_pol) > 3:
                trs.append([filtered_pol[0], filtered_pol[1], filtered_pol[2]])
                del filtered_pol[1]
            trs.append(filtered_pol)
            return trs

    def first_point_inside(self, extent, tr1):
        for k, p in enumerate(tr1):
            if extent.isIn(p[0], p[1]):
                return k
        print('traingle outside extent', tr1)
        return None

    def createQuarters(self):
        center = self.ee_utm.getCenter()
        utm_epsg = "32636"
        quarters = [
            Extent(self.extent[0][0], self.extent[0][1], center[0], center[1], utm_epsg),
            Extent(center[0], center[1], self.extent[1][0], self.extent[1][1], utm_epsg),
            Extent(self.extent[0][0], center[1], center[0], self.extent[1][1], utm_epsg),
            Extent(center[0], self.extent[0][1], self.extent[1][0], center[1], utm_epsg)
        ]
        return quarters

    def cut_by_polygon(self, polygon : SimplePolygon):
        extent = polygon.getExtent()
        new_ee = ExtendedExchangeFormat()
        new_ee.images = copy.deepcopy(self.ee.images)
        new_ee.parts = []

        for part in self.ee_utm.parts:
            new_part = {'subparts': []}
            for subpart in part['subparts']:
                new_subpart = {}
                for key in subpart.keys():
                    if key not in ['vertices', 'texCoords', 'indices']:
                        new_subpart[key] = copy.deepcopy(subpart[key])

                src_subpart_vertices = subpart['vertices']
                src_subpart_texCoords = subpart['texCoords']
                origin = self.ee_utm.origin

                vertices = []
                texCoords = []
                ind = 0
                cnt = 0
                lookup = {}
                for vt in src_subpart_vertices:
                    va = [vt[0] + origin[0], vt[1] + origin[1], vt[2] + origin[2]]
                    if polygon.isIn(va[0], va[1]):
                        vertices.append(vt)
                        texCoords.append(src_subpart_texCoords[cnt])
                        lookup[cnt] = ind
                        ind += 1
                    else:
                        lookup[cnt] = None

                    cnt += 1

                if len(vertices) == 0:
                    continue

                #########################
                indices_SRC = subpart['indices']
                indices = []
                ind = 0
                cnt = 0
                for tr in indices_SRC:
                    if lookup[tr[0]] is None or lookup[tr[1]] is None or lookup[tr[2]] is None:
                        triangle_extent = self.calc_triangle_extent(tr, src_subpart_vertices)
                        if triangle_extent.intersect(extent):
                            # @todo: check intersection between polygons
                            tr_new = [lookup[tr[0]], lookup[tr[1]], lookup[tr[2]]]
                            new_trs = self.cut_triangle_by_polygon(polygon, vertices, src_subpart_vertices, texCoords,
                                                        src_subpart_texCoords, tr, tr_new)
                            indices.extend(new_trs)
                    else:
                        tr_new = [lookup[tr[0]], lookup[tr[1]], lookup[tr[2]]]
                        indices.append(tr_new)
                    cnt += 1
                new_subpart['indices'] = indices
                new_subpart['vertices'] = vertices
                new_subpart['texCoords'] = texCoords

                new_part['subparts'].append(new_subpart)
            new_ee.parts.append(new_part)

        # ee.parts

        out_ee = new_ee.project("epsg:32636", "epsg:4978", dst_origin=self.ee.origin)
        return out_ee

    def cut_by_extent(self, extent):
        new_ee = ExtendedExchangeFormat()
        new_ee.images = copy.deepcopy(self.ee.images)
        new_ee.parts = []

        for part in self.ee_utm.parts:
            new_part = {'subparts': []}
            for subpart in part['subparts']:
                new_subpart = {}
                for key in subpart.keys():
                    if key not in ['vertices', 'texCoords', 'indices']:
                        new_subpart[key] = copy.deepcopy(subpart[key])

                src_subpart_vertices = subpart['vertices']
                src_subpart_texCoords = subpart['texCoords']
                origin = self.ee_utm.origin

                vertices = []
                texCoords = []
                ind = 0
                cnt = 0
                lookup = {}
                for vt in src_subpart_vertices:
                    va = [vt[0] + origin[0], vt[1] + origin[1], vt[2] + origin[2]]
                    if extent.isIn(va[0], va[1]):
                        vertices.append(vt)
                        texCoords.append(src_subpart_texCoords[cnt])
                        lookup[cnt] = ind
                        ind += 1
                    else:
                        lookup[cnt] = None

                    cnt += 1

                if len(vertices) == 0:
                    continue

                #########################
                indices_SRC = subpart['indices']
                indices = []
                ind = 0
                cnt = 0
                for tr in indices_SRC:
                    if lookup[tr[0]] is None or lookup[tr[1]] is None or lookup[tr[2]] is None:
                        triangle_extent = self.calc_triangle_extent(tr, src_subpart_vertices)
                        if triangle_extent.intersect(extent):
                            tr_new = [lookup[tr[0]], lookup[tr[1]], lookup[tr[2]]]
                            new_trs = self.cut_triangle(extent, vertices, src_subpart_vertices, texCoords,
                                                        src_subpart_texCoords, tr, tr_new)
                            indices.extend(new_trs)
                    else:
                        tr_new = [lookup[tr[0]], lookup[tr[1]], lookup[tr[2]]]
                        indices.append(tr_new)
                    cnt += 1
                new_subpart['indices'] = indices
                new_subpart['vertices'] = vertices
                new_subpart['texCoords'] = texCoords

                new_part['subparts'].append(new_subpart)
            new_ee.parts.append(new_part)

        # ee.parts

        out_ee = new_ee.project("epsg:32636", "epsg:4978", dst_origin=self.ee.origin)
        return out_ee

    def calc_triangle_extent(self, tr, vertices):
        stc = [vertices[tr[0]], vertices[tr[1]],
               vertices[tr[2]]]
        ax_min = min(stc[0][0], stc[1][0], stc[2][0])
        ay_min = min(stc[0][1], stc[1][1], stc[2][1])
        ax_max = max(stc[0][0], stc[1][0], stc[2][0])
        ay_max = max(stc[0][1], stc[1][1], stc[2][1])
        return Extent(ax_min, ay_min, ax_max, ay_max, '32636')

    def split(self):
        quarters = self.createQuarters()
        result = []
        for bbox in quarters:
            result.append(self.cut_by_extent(bbox))
        # bbox = quarters[3]
        # print(bbox.asTuple())
        # result = [self.cut_by_extent(bbox)]
        return result
