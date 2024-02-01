from TileScheme.WorldCRS84Quad import WorldCRS84Quad
from TileScheme.WmtsTile import WmtsTile


class TiledExtent:
    def __init__(self, x_min: int = 0, y_min: int = 0, x_max: int = 0, y_max: int = 0, level: int = 15):
        self.set(x_min, y_min, x_max, y_max, level)

    def tiles(self):
        for x_cursor in range(self.x_min, self.x_max+1):
            for y_cursor in range(self.y_min, self.y_max+1):
                yield WmtsTile(x_cursor, y_cursor, self.level)

    @staticmethod
    def fromExtent(extent, level):
        w = WorldCRS84Quad()
        extent_4326 = extent.transform('4326')
        x1, y1, _ = w.positionToTileXY(extent_4326.x_min, extent_4326.y_min, level)
        x2, y2, _ = w.positionToTileXY(extent_4326.x_max, extent_4326.y_max, level)
        x_min = min(x1, x2)
        x_max = max(x1, x2)
        y_min = min(y1, y2)
        y_max = max(y1, y2)
        return TiledExtent(x_min, y_min, x_max, y_max, level)

    def getMinimalPoint(self):
        return self.x_min, self.y_min

    def getMaximalPoint(self):
        return self.x_max, self.y_max

    def set(self, x_min, y_min, x_max, y_max, level):
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max
        self.level = level

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
        if not self.level == e.level:
            return None

        return TiledExtent(max(self.x_min, e.x_min), max(self.y_min, e.y_min),
                           min(self.x_max, e.x_max), min(self.y_max, e.y_max), e.level)
