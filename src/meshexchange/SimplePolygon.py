from shapely import Polygon, Point

from meshexchange.Surface.Extent import Extent


class SimplePolygon:
    def __init__(self, polygon=None, epsg='32636'):
        self.polygon = polygon
        self.epsg = epsg

    def isIn(self, x, y):
        """ returns true if give coord inside polygon """
        return self.polygon.contains(Point(x, y))

    def getExtent(self):
        """ returns polygon extent """
        return Extent(*self.polygon.bounds, self.epsg)

    def coords(self):
        return list(self.polygon.exterior.coords)

    def relation(self, polygon: Polygon):

        if self.polygon.contains(polygon):
            return 2
        if self.polygon.intersects(polygon):
            return 1

        return 0

    @staticmethod
    def fromCoords(coords, epsg):
        p = Polygon(coords)
        return SimplePolygon(p, epsg)
