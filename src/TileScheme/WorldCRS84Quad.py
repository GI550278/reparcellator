import math

from meshexchange.Surface.Extent import Extent


class WorldCRS84Quad:
    def __init__(self):
        self._numberOfLevelZeroTilesX = 2
        self._numberOfLevelZeroTilesY = 1
        self._rectangle = Extent(-180, -90, 180, 90)

    def tileXYToExtent(self, x, y, level) -> Extent:
        rectangle = self._rectangle

        xTiles = self._numberOfLevelZeroTilesX << level
        yTiles = self._numberOfLevelZeroTilesY << level

        xTileWidth = rectangle.getWidth() / xTiles
        west = x * xTileWidth + rectangle.x_min
        east = (x + 1) * xTileWidth + rectangle.x_min
        yTileHeight = rectangle.getHeight() / yTiles
        north = rectangle.y_max - y * yTileHeight
        south = rectangle.y_max - (y + 1) * yTileHeight
        return Extent(west, south, east, north)

    def positionToTileXY(self, longitude, latitude, level):
        rectangle = self._rectangle
        if not rectangle.isIn(longitude, latitude):
            return None

        xTiles = self._numberOfLevelZeroTilesX << level
        yTiles = self._numberOfLevelZeroTilesY << level
        xTileWidth = rectangle.getWidth() / xTiles
        yTileHeight = rectangle.getHeight() / yTiles
        xTileCoordinate = int(math.floor((longitude - rectangle.x_min) / xTileWidth))
        if xTileCoordinate >= xTiles:
            xTileCoordinate = xTiles - 1

        yTileCoordinate = int(math.floor((rectangle.y_max - latitude) / yTileHeight))
        if yTileCoordinate >= yTiles:
            yTileCoordinate = yTiles - 1

        return xTileCoordinate, yTileCoordinate, level
