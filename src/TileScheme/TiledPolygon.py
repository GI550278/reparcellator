from TileScheme.TiledExtent import TiledExtent
from TileScheme.WmtsTile import WmtsTile
from meshexchange.SimplePolygon import SimplePolygon


class TiledPolygon:
    def __init__(self, simple_model_polygon, level):
        self.level = level
        self.simple_model_polygon = simple_model_polygon
        self.model_extent = self.simple_model_polygon.getExtent()
        self.tiled_extent = TiledExtent.fromExtent(self.model_extent, level)

    def isTileCoordsIn(self, x, y):
        tile = WmtsTile(x, y, self.level)
        return self.isTileIn(tile)

    def isTileIn(self, tile):
        relation = self.simple_model_polygon.relation(tile.polygon)
        if relation == 0:
            return False
        return True

    def tiles(self):
        for tile in self.tiled_extent.tiles():
            relation = self.simple_model_polygon.relation(tile.polygon)
            if relation == 0:
                continue
            # relation: 1 - contains, 2 - intersects
            yield tile
