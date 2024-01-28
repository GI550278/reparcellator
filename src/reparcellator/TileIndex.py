import geopandas as gpd
from shapely import Polygon


class TileIndex:
    def __init__(self, epsg=4326):
        self.epsg = epsg
        self.path = []
        self.coords = []
        self.density = []
        self.level = []

    def append(self, path='', polygon_coords=[], density=0, level=0):
        if len(polygon_coords) < 3:
            return
        self.path.append(path)
        polygon = Polygon(polygon_coords)
        self.coords.append(polygon)
        self.density.append(density)
        self.level.append(level)

    def export_to_geopackage(self, file_name):
        if len(self.path) == 0:
            return
        df = {'path': self.path, 'geometry': self.coords, 'density': self.density, 'level': self.level}
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs=f"EPSG:{self.epsg}")
        gdf.to_file(file_name, driver='GPKG')
