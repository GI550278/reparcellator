from shapely import Polygon

from TileScheme.WmtsTile import WmtsTile
from meshexchange.Surface.Extent import Extent


t16 = WmtsTile(78100,21280,16)
for t in t16.children():
    print(t.getName())
    print(t16.polygon.intersects(t.polygon))
    print(t16.extent.intersect(t.extent))
exit()
t16 = WmtsTile(78100,21280,16)
t17 = WmtsTile(156201, 42561, 17)
print(t16.polygon)
print(t17.polygon)

print(t16.extent.asArray())
print(t17.extent.asArray())


# x, y = 643308.852, 3491610.160
# temp_extent = Extent.fromUtm36Dimensions(x, y, 100, 100)
# model_polygon = Polygon(temp_extent.asPolygon())
