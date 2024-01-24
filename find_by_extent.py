import pathlib
from b3dmlib.FilterTileSet import FilterTileSet
import urllib.request
import requests

from meshexchange.B3DMModule import B3DMModule
from meshexchange.SimplePolygon import SimplePolygon
from meshexchange.Surface.Extent import Extent
from shapely import Polygon


class ModelPrinter:
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst
        self.main_polygon = None
        # @todo: this prefix should be retrived from the self.src
        self.path_prefix = r'\3dtiles\2'

    def print_tile(self, data):
        output_directory = str(data['src'].parent).replace(self.path_prefix, self.dst).replace('\\', '/')
        osgb_dir = pathlib.Path(output_directory)
        if not osgb_dir.exists():
            osgb_dir.mkdir(parents=True, exist_ok=True)
        file_name = output_directory + '/' + str(data['src'].name)
        uri = str(data['src']).replace(self.path_prefix, self.src).replace('\\', '/')
        tile_extent = Extent.fromRad(data['extent']).transform('32636')
        tile_polygon = Polygon(tile_extent.asPolygon())
        relation = self.main_polygon.relation(tile_polygon)

        if relation == 0:
            return False, False
        if relation == 1:
            print('TOUCH:', uri)

            return True, True
        else:
            print('IN', uri)
            ModelPrinter.download_file(uri, file_name)
            b = B3DMModule()
            ee = b.b3dmToExtendedExchange(file_name, self.dst + '/image.jpg', 'image.jpg', 0)

            b.extendedExchangeTob3dm(ee, file_name.replace('.b3dm', ''))
            return True, True

    @staticmethod
    def download_file(uri, file_name):
        mp3file = urllib.request.urlopen(uri)
        with open(file_name, 'wb') as output:
            output.write(mp3file.read())

    def print_tiles(self, polygon_coords):
        # @todo: verify polygon
        self.main_polygon = SimplePolygon.fromCoords(polygon_coords, '32636')
        w = FilterTileSet(self.src, self.dst)
        w.processTileSet('', 'tileset.json', self.print_tile)


if __name__ == '__main__':
    mc = ModelPrinter(src="http://localhost:8000/3dtiles/2",
                      dst=r"c:\temp\copy_2_v8")
    e = Extent.fromRad([0.6025426069863078,
                        0.5509374200611408,
                        0.6025520557542373,
                        0.5509516260878613])
    extent_utm = e.transform('32636').buffer(10)
    polygon = extent_utm.asPolygon()
    mc.print_tiles(polygon)
    print('Done')
