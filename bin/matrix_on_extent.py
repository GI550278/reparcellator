from shapely import Polygon
from meshexchange.Surface.Extent import Extent
from reparcellator.Reparcellation import Reparcellation

# this is temp. polygon of the model will be given
# x, y = 643308.852, 3491610.160
# temp_extent = Extent.fromUtm36Dimensions(x, y, 100, 100)
temp_extent = Extent(638763,3482796,649457,3492694,'32636')
model_polygon = Polygon(temp_extent.asPolygon())
# end of temp block

r = Reparcellation(
    index_path=r"C:\temp\best\index_3_v1.gpkg",
    dst=r'c:\temp\best\model_3',
    model_polygon=model_polygon,
    db_path=r"c:\temp\best\best_db.db"
)
r.initiate()
# r.min_level = 15
# r.max_level = 18
r.create_all_tiles()
print('done creating tiles')
r.create_tileset_json()
print('done writing tileset')
print('Done')
