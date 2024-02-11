from shapely import Polygon
from meshexchange.Surface.Extent import Extent
from reparcellator.Reparcellation import Reparcellation

# this is temp. polygon of the model will be given
x, y = 643308.852, 3491610.160
temp_extent = Extent.fromUtm36Dimensions(x, y, 100, 100)
model_polygon = Polygon(temp_extent.asPolygon())
# end of temp block

r = Reparcellation(
    index_path=r"C:\temp\index_25_v2_copy.gpkg",
    dst=r'C:\Users\sguya\Downloads\cesium-starter-app-master\public\wmts_test_v1\flip_yz_v9',
    model_polygon=model_polygon
)
r.initiate()
r.min_level = 15
r.max_level = 18
r.create_all_tiles()
r.create_tileset_json()
print('Done')
