import json
import logging
import os
import pathlib
from datetime import datetime

from TileScheme.ModelWmtsCutter import ModelWmtsCutter
from TileScheme.TiledExtent import TiledExtent
from TileScheme.TiledPolygon import TiledPolygon
from meshexchange.SimplePolygon import SimplePolygon
from reparcellator.ContinuousDB import ContinuousDB


class Reparcellation:
    """
    Using 3dtile set index created by find_by_extent.py
    Converts the 3dtile set to WMTS tiles in given polygon
    """

    def __init__(self, **kwargs):
        self.index_path = kwargs['index_path']
        self.dst = kwargs['dst']
        self.skip_tile_creation = kwargs['skip_tile_creation'] if 'skip_tile_creation' in kwargs else False
        self.model_polygon = kwargs['model_polygon']
        self.db_path = kwargs['db_path'] if 'db_path' in kwargs else 'c_test_db.db'
        self.db = None
        self.model_cutter = None
        self.simple_model_polygon = None
        self.extent = None
        self.min_level = None
        self.max_level = None

    def initiate(self):
        self.db = ContinuousDB(self.db_path)
        self.db.create_new_db()
        # @todo: make this changeble
        self.db.setDate(datetime.now())
        self.db.setId('1')
        self.model_cutter = ModelWmtsCutter(self.index_path)
        self.model_cutter.calculate_level_map()
        self.min_level = min(self.model_cutter.level_map.keys())
        self.max_level = max(self.model_cutter.level_map.keys())

        output_dir = pathlib.Path(self.dst)
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        self.simple_model_polygon = SimplePolygon(self.model_polygon, '32636')
        self.extent = self.simple_model_polygon.getExtent()

    def create_all_tiles(self):
        for level in range(self.min_level, self.max_level + 1):
            tiled_extent = TiledExtent.fromExtent(self.extent, level)
            for tile in tiled_extent.tiles():
                if self.model_polygon.contains(tile.polygon):
                    self.model_cutter.cut(tile.x, tile.y, tile.z, self.dst + '/' + tile.getName())
                    self.db.save_tile(tile,  self.dst + '/' + tile.getName())
                elif self.model_polygon.intersects(tile.polygon):
                    i = self.model_polygon.intersection(tile.polygon)
                    self.model_cutter.cut(tile.x, tile.y, tile.z, self.dst + '/' + tile.getName())
                    self.db.save_tile(tile,  self.dst + '/' + tile.getName())
        self.db.close()
    def tile_to_json(self, tile):
        geometricError = 3000
        z_max = 200
        z_min = -200
        region = tile.extent.toRadArray() + [z_min, z_max]
        uri = tile.getName() + '.b3dm'
        children = []

        if tile.z < self.max_level:
            tiledPolygon = TiledPolygon(self.simple_model_polygon, tile.z + 1)
            print(f'Sub tiles of {tile.getName()}:')
            print('-' * 80)
            for child_tile in tile.children():
                if tiledPolygon.isTileIn(child_tile):
                    # model_cutter.cut(tile.x, tile.y, tile.z, dst + '/' + tile.getName())

                    if os.path.exists(self.dst + '/' + child_tile.getName() + '.b3dm'):
                        children.append(self.tile_to_json(child_tile))
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

    def create_root_multiple(self, tiles):
        # @todo: calc geometric error
        genealGeometricError = 3000
        geometricError = 3000
        z_max = 200
        z_min = -200
        rad_union_extent = tiles[0].extent
        for tile in tiles:
            if rad_union_extent is None:
                rad_union_extent = tile.extent
            else:
                rad_union_extent = tile.extent.union(rad_union_extent)
        region = rad_union_extent.toRadArray() + [z_min, z_max]
        children = []
        for child_tile in tiles:
            if os.path.exists(self.dst + '/' + child_tile.getName() + '.b3dm'):
                children.append(self.tile_to_json(child_tile))
                print(f"Tile {child_tile.getName()} added")
            else:
                print(f"Tile {child_tile.getName()} file not found")
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

    def create_root(self, tile):
        # @todo: calc geometric error
        genealGeometricError = 3000
        geometricError = 3000
        z_max = 200
        z_min = -200
        region = tile.extent.toRadArray() + [z_min, z_max]
        children = []
        tiledPolygon = TiledPolygon(self.simple_model_polygon, tile.z + 1)
        for child_tile in tile.children():
            if tiledPolygon.isTileIn(child_tile):
                if os.path.exists(self.dst + '/' + child_tile.getName() + '.b3dm'):
                    children.append(self.tile_to_json(child_tile))
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

    def create_tileset_json(self):
        tiledPolygon = TiledPolygon(self.simple_model_polygon, self.min_level)
        tiles = list(tiledPolygon.tiles())

        if tiles is None or len(tiles) == 0:
            logging.error("No start tile")
            exit()

        # if not self.skip_tile_creation:
        #     r.create_all_tiles()

        tileset = self.create_root_multiple(tiles)
        output_tileset = rf'{self.dst}\tileset.json'
        with open(output_tileset, 'w') as f:
            json.dump(tileset, f)
