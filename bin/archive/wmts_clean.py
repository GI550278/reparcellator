import requests
from shapely import Polygon, from_wkt, area

from TileScheme.WorldCRS84Quad import WorldCRS84Quad
from meshexchange.B3DMModule import B3DMModule
from meshexchange.Surface.Extent import Extent
from src.reparcellator.TileIndex import TileIndex
import geopandas as gpd

# producing wmts tile

# Step 1 - Find wmts tile level 18 in given coordinate:
qd = WorldCRS84Quad()
level = 19
ex = Extent.fromUtm36Dimensions(641902.038, 3493981.625, 1, 1)
ex = ex.transform('4236')
p = ex.centroid()
x1, y1, l1 = qd.positionToTileXY(p[0], p[1], level)
print(x1,y1,l1)
exit()
wmts_tile_extent = qd.tileXYToExtent(x1, y1, l1)
wmts_tile_polygon = Polygon(wmts_tile_extent.transform('32636').asPolygon())
wmts_tile_area = wmts_tile_polygon.area

# ranges = {}
# for level in range(7,25):
#     x1, y1, l1 = qd.positionToTileXY(p[0], p[1], level)
#     wmts_tile_extent = qd.tileXYToExtent(x1, y1, l1)
#     wmts_tile_polygon = Polygon(wmts_tile_extent.transform('32636').asPolygon())
#     wmts_tile_area = wmts_tile_polygon.area
#     print(level, wmts_tile_area*0.8)
#     ranges[level] = wmts_tile_area*0.8
# print(ranges)
# exit()
ranges = {7: 16558599837.826073, 8: 4151883385.7169876, 9: 1036457280.5085238, 10: 258925801.94720307,
          11: 64707927.67332694, 12: 16181847.239898676, 13: 4045829.2137908917, 14: 1011381.3806769031,
          15: 252835.8520644892, 16: 63209.68092086297, 17: 15802.509970991265, 18: 3950.6162754023653,
          19: 987.6517510093832, 20: 246.91264802761944, 21: 61.72818391500374, 22: 15.432043239845928,
          23: 3.8580104657880514, 24: 0.9645026598606032}
# range for each level define the 80% of the wmts tile on that level
# original_levels for each level in the index, the median area


# Step 2 - Open Index

# index_path = r"O:\Data\3DBest\3dtiles_index\index_25_v2.gpkg"
index_path = r"C:\temp\index_25_v2_copy.gpkg"
index_3dtiles = gpd.GeoDataFrame.from_file(index_path)
index_3dtiles.crs = f"EPSG:32636"

res = index_3dtiles.groupby(['level']).agg({'area': "median", 'level': 'max'})
# print(res.head())
original_levels = {}
for feature in res.iterrows():
    level = int(feature[1]['level'])
    area = feature[1]['area']
    original_levels[level] = area
print(original_levels)
max_original_level = max(original_levels.keys())
# the purpose build a function level->original_level
# level->80% wmts area -> find smallest median area that is above (80% wmts area)->original_level
level_map = {}
for level, wmts_area in ranges.items():
    best_median_area = 9e99
    best_original_level = -1
    for original_level, median_area in original_levels.items():
        if median_area > wmts_area and best_median_area > median_area:
            best_median_area = median_area
            best_original_level = original_level
    if best_original_level > 0:
        level_map[level] = best_original_level
    if best_original_level == max_original_level:
        break
print(level_map)

# Step 2 - Select all tiles that intersect wmts-tile on desired level
target_level = level_map[l1]
print(f'target_level={target_level}')
while target_level>6:
    subset = index_3dtiles[(index_3dtiles.level == target_level) & (
            index_3dtiles.geometry.intersects(wmts_tile_polygon) | index_3dtiles.geometry.contains(wmts_tile_polygon))]
    if subset.size > 0:
        break
    else:
        target_level -= 1

print(f'target_level={target_level}')
file_name = rf"c:\temp\wmts_clean_covering_tiles_{l1}_v2.gpkg"
subset.to_file(file_name, driver='GPKG')

file_name = rf"c:\temp\wmts_clean_tile_polygon_{l1}_v2.gpkg"
df = {'path': [''], 'geometry': [wmts_tile_polygon]}
gdf = gpd.GeoDataFrame(df, geometry='geometry', crs=f"EPSG:32636")
gdf.to_file(file_name, driver='GPKG')
print('Done.')
# for feature in subset.iterrows():
#     print(feature[1])
# now level maps to best_level
# @todo: check if best_level covers the tile



print('Done.')

# todo:
# calculate area to each level in the original
# original area is matched to level that correspond to area
# min[level] : original area > wmts_area(level)*0.8
# this defines ranges for areas each range is mapped to different level
