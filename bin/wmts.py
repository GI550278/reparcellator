import requests
from shapely import Polygon, from_wkt, area

from TileScheme.WorldCRS84Quad import WorldCRS84Quad
from meshexchange.B3DMModule import B3DMModule
from meshexchange.Surface.Extent import Extent
from src.reparcellator.TileIndex import TileIndex
import geopandas as gpd

#
# qd = WorldCRS84Quad()

# x, y, z = 211, 312, 11
# ex = qd.tileXYToExtent(x, y, z)
# print(ex.asArray())
# print(ex.transform('32636').asArray())
#
# p = ex.centroid()
# x1, y1, l1 = qd.positionToTileXY(p[0], p[1], z)
# print(x1, y1, l1)
#
# level = 1
# resolution = 0.703125000000000*(2**(-level))
# print(resolution)
ex = Extent.fromUtm36Dimensions(640561.40806, 3494471.46074, 1, 1)
ex = ex.transform('4236')
p = ex.centroid()

z = 18
resolution = 0.703125000000000 * (2 ** (-z))

qd = WorldCRS84Quad()
x1, y1, l1 = qd.positionToTileXY(p[0], p[1], z)
ex = qd.tileXYToExtent(x1, y1, l1)
print(Polygon(ex.transform('32636').asPolygon()))
p = Polygon(ex.transform('32636').asPolygon())

file_name = r"c:\temp\geopackage_2.gpkg"
df = {'path': [''], 'geometry': [p]}
gdf = gpd.GeoDataFrame(df, geometry='geometry', crs=f"EPSG:32636")
# gdf.to_file(file_name, driver='GPKG')

path = r"C:\temp\index_channel_2_v1.gpkg"
gdf2 = gpd.GeoDataFrame.from_file(path)
gdf2.crs = f"EPSG:32636"
# print(gdf.head())
# the correct form:
subset = gdf2[gdf2.geometry.intersects(p)]
# - subset = gdf2[gdf2.geometry.within(p)]
# - subset = gdf2.sjoin(gdf)
# print(subset.head())
#
#
# file_name = r"c:\temp\geopackage_subset2.gpkg"
# subset.to_file(file_name, driver='GPKG')


print(resolution)
for feature in subset.iterrows():
    uri = feature[1]['path']
    pol = feature[1]['geometry']
    print(uri)
    print('area:', area(pol))
    b = B3DMModule()
    r = requests.get(uri)
    if r.status_code == 200:
        print('IN', uri)
        ee = b.b3dmPayloadToExtendedExchange(bytearray(r.content))
        num = ee.calculateNumberOfVertices()
        density = num / area(pol)
        if density < 1e-4:
            print('num:', num)
            print('density:', density)
            print('madad:', resolution/density)

print('Done.')
