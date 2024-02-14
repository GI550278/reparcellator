from math import floor

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
        return f"{self.z}_{self.x}_{self.y}"

    def getFullPath(self, version=0, extension='b3dm'):
        if self.z < 7:
            return None
        directory = ''
        level = 7
        while level < self.z:
            directory += f'/{self.getNameAtLevel(level)}'
            level += 4

        directory += f'/{self.getName()}/{self.getName()}_{version}.{extension}'
        return directory

    def getCoordsAtLevel(self, level):
        x, y, z = self.x, self.y, self.z
        while z >= level:
            if z == level:
                return x, y, z

            x1 = floor(x / 2)
            y1 = floor(y / 2)
            z1 = z - 1
            x, y, z = x1, y1, z1

    def getNameAtLevel(self, level):
        x, y, z = self.getCoordsAtLevel(level)
        return f"{z}_{x}_{y}"
