import json
import logging
import os.path
import pathlib

from shapely import Polygon
from TileScheme.TiledExtent import TiledExtent
from TileScheme.TiledPolygon import TiledPolygon
from TileScheme.ModelWmtsCutter import ModelWmtsCutter
from meshexchange.SimplePolygon import SimplePolygon
from meshexchange.Surface.Extent import Extent

"""
Using 3dtile set index created by find_by_extent.py
Converts the 3dtile set to WMTS tiles in given polygon

@todo:  remove print, convert to class
"""

index_path = r"C:\temp\index_25_v2_copy.gpkg"
dst = r'C:\Users\sguya\Downloads\cesium-starter-app-master\public\wmts_test_v1\flip_yz_v7'
skip_tile_creation = False
# this is temp. polygon of the model will be given
x, y = 643308.852, 3491610.160
temp_extent = Extent.fromUtm36Dimensions(x, y, 100, 100)
model_polygon = Polygon(temp_extent.asPolygon())
# end of temp block


model_cutter = ModelWmtsCutter(index_path)
model_cutter.calculate_level_map()

osgb_dir = pathlib.Path(dst)
if not osgb_dir.exists():
    osgb_dir.mkdir(parents=True, exist_ok=True)

simple_model_polygon = SimplePolygon(model_polygon, '32636')
extent = simple_model_polygon.getExtent()

min_level = 15 #min(model_cutter.level_map.keys())
max_level = 19 # max(model_cutter.level_map.keys())
tiledPolygon = TiledPolygon(simple_model_polygon, min_level)
the_tile = None
for tile in tiledPolygon.tiles():
    the_tile = tile
    break

if the_tile is None:
    logging.error("No start tile")
    exit()

if not skip_tile_creation:
    # extent to tile coords extent
    for level in range(min_level, max_level + 1):
        tiledExtent = TiledExtent.fromExtent(extent, level)
        print(level, tiledExtent.asArray())
        for tile in tiledExtent.tiles():
            if model_polygon.contains(tile.polygon):
                print('in:', tile.x, tile.y, tile.z)
                model_cutter.cut(tile.x, tile.y, tile.z, dst + '/'+tile.getName())
            elif model_polygon.intersects(tile.polygon):
                i = model_polygon.intersection(tile.polygon)
                print('bound:', tile.x, tile.y, tile.z, i.area)
                model_cutter.cut(tile.x, tile.y, tile.z, dst + '/'+tile.getName())
            else:
                print('excluded:', tile.x, tile.y, tile.z)
                pass

    print('Done creating tiles')

def tile_to_json(tile):
    geometricError = 3000
    z_max = 200
    z_min = -200
    region = tile.extent.toRadArray() + [z_min, z_max]
    uri = tile.getName() + '.b3dm'
    children = []

    if tile.z < max_level:
        tiledPolygon = TiledPolygon(simple_model_polygon, tile.z + 1)
        print(f'Sub tiles of {tile.getName()}:')
        print('-'*80)
        for child_tile in tile.children():
            if tiledPolygon.isTileIn(child_tile):
                # model_cutter.cut(tile.x, tile.y, tile.z, dst + '/' + tile.getName())

                if os.path.exists(dst + '/' + child_tile.getName() + '.b3dm'):
                    children.append(tile_to_json(child_tile))
                    print(f"Tile {child_tile.getName()} added")
                else:
                    print(f"Tile {child_tile.getName()} file not found")
            else:
                print(f"Tile {child_tile.getName()} not in the extent")

    return {
        "boundingVolume": {
            "region": region
        },
        "refine": "REPLACE",
        "geometricError": geometricError,
        "content": {
            "uri": uri,
            "boundingVolume": {
                "region": region
            }
        },
        "children": children
    }


def create_root(tile):
    # @todo: calc geometric error
    genealGeometricError = 3000
    geometricError = 3000
    z_max = 200
    z_min = -200
    region = tile.extent.toRadArray() + [z_min, z_max]
    children = []
    tiledPolygon = TiledPolygon(simple_model_polygon, tile.z + 1)
    for child_tile in tile.children():
        if tiledPolygon.isTileIn(child_tile):
            if os.path.exists(dst + '/' + child_tile.getName() + '.b3dm'):
                children.append(tile_to_json(child_tile))
                print(f"Tile {child_tile.getName()} added")
            else:
                print(f"Tile {child_tile.getName()} file not found")
        else:
            print(f"Tile {child_tile.getName()} not in the extent")
    return {
        "asset": {
            "version": "1.0"
        },
        "geometricError": genealGeometricError,
        "refine": "REPLACE",
        "root": {
            "boundingVolume": {
                "region": region
            },
            "refine": "REPLACE",
            "geometricError": geometricError,
            "children": children
        }
    }


tileset = create_root(the_tile)
# output_tileset = dst + '/tileset.json'
output_tileset = rf'{dst}\tileset.json'
with open(output_tileset, 'w') as f:
    json.dump(tileset, f)
print("Done creating tileset.json")
