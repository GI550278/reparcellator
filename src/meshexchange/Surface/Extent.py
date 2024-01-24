import math

from pyproj import Transformer


class Extent:
    def __init__(self, x_min=0, y_min=0, x_max=0, y_max=0, epsg="4326"):
        self.set(x_min, y_min, x_max, y_max, epsg)

    def centroid(self):
        return [ self.x_min+(self.x_max - self.x_min)/2, self.y_min+(self.y_max - self.y_min)/2]

    def buffer(self, b):
        return Extent(self.x_min - b, self.y_min - b, self.x_max + b, self.y_max + b, self.epsg)

    def buffer_procent(self, p):
        bx = (self.x_max - self.x_min) * p
        by = (self.y_max - self.y_min) * p
        return Extent(self.x_min - bx, self.y_min - by, self.x_max + bx, self.y_max + by, self.epsg)

    @staticmethod
    def fromRad(extent_rad):
        extent_deg = list(map(lambda x: x * 180 / math.pi, extent_rad[0:4]))
        return Extent(*extent_deg, "4326")

    def toRadArray(self):
        if self.epsg == "4326":
            return list(map(lambda x: x * math.pi / 180, self.asArray()))
        else:
            return self.transform("4326").toRadArray()

    @staticmethod
    def fromGeoDimensions(x_min, y_min, width, height):
        e = Extent()
        e.setWithDimensions(x_min, y_min, width, height, "4326")
        return e

    @staticmethod
    def fromUtm36Dimensions(x_min, y_min, width, height):
        e = Extent()
        e.setWithDimensions(x_min, y_min, width, height, "32636")
        return e

    def getMinimalPoint(self):
        return self.x_min, self.y_min

    def getMaximalPoint(self):
        return self.x_max, self.y_max

    def set(self, x_min, y_min, x_max, y_max, epsg="4326"):
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max
        self.epsg = epsg

    def setWithDimensions(self, x_min, y_min, width, height, epsg="4326"):
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_min + width
        self.y_max = y_min + height
        self.epsg = epsg

    def getWidth(self):
        return self.x_max - self.x_min

    def getHeight(self):
        return self.y_max - self.y_min

    def getArea(self):
        return self.getWidth() * self.getHeight()

    def asTuple(self):
        return self.x_min, self.y_min, self.x_max, self.y_max

    def asArray(self):
        return [self.x_min, self.y_min, self.x_max, self.y_max]

    def asPolygon(self):
        return [[self.x_min, self.y_min], [self.x_min, self.y_max], [self.x_max, self.y_max], [self.x_max, self.y_min]]

    def flipXY(self):
        return Extent(self.y_min, self.x_min, self.y_max, self.x_max, self.epsg)

    def transform(self, epsg=None):
        if epsg is None:
            return Extent(self.x_min, self.y_min, self.x_max, self.y_max, self.epsg)
        else:
            transformer = Transformer.from_crs(f"epsg:{self.epsg}", f"epsg:{epsg}")
            if self.epsg == '4326':
                bottom_left = list(transformer.transform(self.y_min, self.x_min))
                top_right = list(transformer.transform(self.y_max, self.x_max))
                k = 0
            else:
                bottom_left = list(transformer.transform(self.x_min, self.y_min))
                top_right = list(transformer.transform(self.x_max, self.y_max))
                k = 1
            xmin = min(bottom_left[k], top_right[k])
            xmax = max(bottom_left[k], top_right[k])

            ymin = min(bottom_left[1 - k], top_right[1 - k])
            ymax = max(bottom_left[1 - k], top_right[1 - k])

            return Extent(xmin, ymin, xmax, ymax, epsg)

    def isIn(self, x, y):
        if self.x_max <= x:
            return False

        if self.x_min >= x:
            return False

        if self.y_max <= y:
            return False

        if self.y_min >= y:
            return False

        return True

    def intersect(self, e):
        if self.x_max < e.x_min:
            return False

        if self.x_min > e.x_max:
            return False

        if self.y_max < e.y_min:
            return False

        if self.y_min > e.y_max:
            return False

        return True

    def intersection(self, e):
        if not self.epsg == e.epsg:
            return None

        return Extent(max(self.x_min, e.x_min), max(self.y_min, e.y_min),
                      min(self.x_max, e.x_max), min(self.y_max, e.y_max), e.epsg)
