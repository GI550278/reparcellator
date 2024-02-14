from pathlib import Path

import geopandas as gpd
import requests
from shapely import intersection

from TileScheme.WmtsTile import WmtsTile
from TileScheme.ranges import ranges


class ModelWmtsCutter:
    """
    the object connects to model index and allows to cut a tile from the model
    """

    def __init__(self, index_path):
        self.main_index = gpd.GeoDataFrame.from_file(index_path)
        self.main_index.crs = f"EPSG:32636"
        self.level_map = None
        self.original_levels = None

    def calculate_level_map(self):

        res = self.main_index.groupby(['level']).agg({'area': "median", 'level': 'max'})

        self.original_levels = {}
        for feature in res.iterrows():
            level = int(feature[1]['level'])
            area = feature[1]['area']
            self.original_levels[level] = area

        max_original_level = max(self.original_levels.keys())
        # the purpose build a function level->original_level
        # level->80% wmts area -> find smallest median area that is above (80% wmts area)->original_level
        self.level_map = {}
        for level, wmts_area in ranges.items():
            best_median_area = 9e99
            best_original_level = -1
            for original_level, median_area in self.original_levels.items():
                if median_area > wmts_area and best_median_area > median_area:
                    best_median_area = median_area
                    best_original_level = original_level
            if best_original_level > 0:
                self.level_map[level] = best_original_level
            if best_original_level == max_original_level:
                break

    def find_relevant_tiles(self, tile):
        # @todo: area can be provided instead of level

        target_level = self.level_map[tile.z]
        while target_level > 6:
            relevant_tiles = self.main_index[(self.main_index.level == target_level) &
                                             (self.main_index.geometry.intersects(tile.polygon) |
                                              self.main_index.geometry.contains(tile.polygon))]
            if relevant_tiles.size > 0:
                return relevant_tiles
            else:
                target_level -= 1
        return None

    def cut(self, x, y, z, file_name, boundary=None):
        tile = WmtsTile(x, y, z)
        if self.level_map is None:
            self.calculate_level_map()
        relevant_tiles = self.find_relevant_tiles(tile)
        if relevant_tiles is None:
            return
        tiles = []
        for k in range(len(relevant_tiles.path)):
            t = {"uri": relevant_tiles.path.iat[k],
                 "polygon": []}  # list(relevant_tiles.geometry.iat[k].exterior.coords)}
            tiles.append(t)
        if boundary is None:
            required_polygon = tile.polygon
        else:
            required_polygon = intersection(boundary, tile.polygon)
        # @todo: extract format from given file name
        format = "b3dm"
        payload = {"tiles": tiles,
                   "polygon": list(required_polygon.exterior.coords),
                   "format": format,
                   "buffer_length": -4}
        r = requests.post('http://localhost:8004/editor/combine', json=payload)
        p = Path(file_name).parent
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)

        file = Path(file_name)
        with open(str(file.with_suffix(f'.{format}')), 'wb') as output:
            output.write(r.content)
