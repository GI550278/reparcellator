from shapely import Polygon

from TileScheme.WorldCRS84Quad import WorldCRS84Quad


class WmtsTile:
    def __init__(self, x, y, z):
        self.tile_scheme = WorldCRS84Quad()
        self.extent = self.tile_scheme.tileXYToExtent(x, y, z)
        self.polygon = Polygon(self.extent.smart_transform('32636').asPolygon())
        self.area = self.polygon.area
        self.x = x
        self.y = y
        self.z = z

    def children(self):
        level = self.z + 1
        x = self.x
        y = self.y
        yield WmtsTile(2 * x, 2 * y, level)
        yield WmtsTile(2 * x + 1, 2 * y, level)
        yield WmtsTile(2 * x, 2 * y + 1, level)
        yield WmtsTile(2 * x + 1, 2 * y + 1, level)

    def getName(self):
        return f"{self.x}_{self.y}_{self.z}"
