import asyncio

from shapely import Polygon
from meshexchange.Surface.Extent import Extent
from reparcellator.Reparcellation import Reparcellation
import sys
from osgeo import ogr
from osgeo import osr

import math
import os
import geopandas as gpd


polygon_shape = r"C:\temp\index_25_v2_extent.shp"



# Read the shapefile
gdf = gpd.read_file(polygon_shape)
for f in gdf.iterrows():
    multi = f[1][5]
for p in multi.geoms:
    model_polygon = p
    break
# # this is temp. polygon of the model will be given
# x, y = 643308.852, 3491610.160
# temp_extent = Extent.fromUtm36Dimensions(x, y, 200, 200)
# model_polygon = Polygon(temp_extent.asPolygon())
# end of temp block

r = Reparcellation(
    index_path=r"C:\temp\index_25_v2_copy.gpkg",
    dst=r'C:\Users\sguya\Downloads\cesium-starter-app-master\public\wmts_test_v1\flip_yz_v28',
    model_polygon=model_polygon,
    db_path=r"C:\temp\best\best_db_v6.db",
    uri_prefix="/public/wmts_test_v1/flip_yz_v28"
)
r.initiate()
r.min_level = 15
r.max_level = 15
#r.create_all_tiles()
asyncio.run(r.create_tiles_in_polygon())
print('done creating tiles')
r.create_tileset_json()
print('done writing tileset')
print('Done')
