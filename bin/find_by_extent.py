import json
import logging
import pathlib
from urllib.parse import urlparse

from meshexchange.Splitter import Splitter
from src.b3dmlib.FilterTileSet import FilterTileSet
import urllib.request
import requests

from src.meshexchange.B3DMModule import B3DMModule
from src.meshexchange.SimplePolygon import SimplePolygon
from src.meshexchange.Surface.Extent import Extent
from src.reparcellator.TileIndex import TileIndex
from shapely import Polygon


class ModelPrinter:
    def __init__(self, src, dst):

        self.dst = dst
        self.main_polygon = None
        self.src_uri = urlparse(src)
        self.ti = TileIndex(32636)

    def print_tile(self, data):
        return True, True
        output_directory = str(data['src'].parent).replace(self.src_uri.path.replace('/', '\\'), self.dst).replace('\\',
                                                                                                                   '/')
        osgb_dir = pathlib.Path(output_directory)
        if not osgb_dir.exists():
            osgb_dir.mkdir(parents=True, exist_ok=True)
        file_name = output_directory + '/' + str(data['src'].name)
        uri = str(data['src']).replace(self.src_uri.path.replace('/', '\\'), self.src_uri.geturl()).replace('\\', '/')
        tile_extent = Extent.fromRad(data['extent']).transform('32636')
        tile_polygon = Polygon(tile_extent.asPolygon())

        if self.main_polygon is None:
            relation = 2
        else:
            relation = self.main_polygon.relation(tile_polygon)

        if relation == 0:
            return False, False
        if relation == 1:
            print('TOUCH:', uri)
            return True, True
        else:
            b = B3DMModule()
            r = requests.get(uri)
            if r.status_code == 200:
                print('IN', uri)
                ee = b.b3dmPayloadToExtendedExchange(bytearray(r.content),Y_UP=True)
                num = ee.calculateNumberOfVertices()
                exact_extent = True
                if exact_extent:
                    sp = Splitter(ee)
                    ext = sp.ee_utm.calculateExtent()
                    extent = Extent(ext[0][0], ext[0][1], ext[1][0], ext[1][1],'32636')
                    # pol = sp.ee_utm.simple_convex_hull()
                    # coords = pol.exterior.coords
                    coords = extent.asPolygon()
                else:
                    coords = tile_extent.asPolygon()
                density = num / tile_extent.getArea()
                self.ti.append(uri, coords, density=density, level=data['level'])

            # ModelPrinter.download_file(uri, file_name)
            # b = B3DMModule()
            # ee = b.b3dmToExtendedExchange(file_name, self.dst + '/image.jpg', 'image.jpg', 0)
            #
            # b.extendedExchangeTob3dm(ee, file_name.replace('.b3dm', ''))
        return True, True

    @staticmethod
    def download_file(uri, file_name):
        mp3file = urllib.request.urlopen(uri)
        with open(file_name, 'wb') as output:
            output.write(mp3file.read())

    def save_tileset(self, tileset, output_tileset):
        return
        with open(output_tileset, 'w') as f:
            json.dump(tileset, f)

    def print_tiles(self, polygon_coords=None):
        if polygon_coords is None:
            self.main_polygon = None
        else:
            # @todo: verify polygon
            self.main_polygon = SimplePolygon.fromCoords(polygon_coords, '32636')

        w = FilterTileSet(self.src_uri.geturl(), self.dst)
        w.processTileSet('', 'tileset.json', self.print_tile, self.save_tileset)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    mc = ModelPrinter(src="http://localhost:8000/3dtiles/2",
                      dst=r"c:\temp\copy_2_v10")
    e = Extent.fromRad([0.6025426069863078,
                        0.5509374200611408,
                        0.6025520557542373,
                        0.5509516260878613])
    extent_utm = e.transform('32636').buffer(10)
    polygon = extent_utm.asPolygon()
    mc.print_tiles(polygon)
    output_file = r"c:\temp\test_index_v6.gpkg"
    mc.ti.export_to_geopackage(output_file)
    print('Done')
