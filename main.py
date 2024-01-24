import pathlib
from b3dmlib.FilterTileSet import FilterTileSet
import urllib.request
import requests

from meshexchange.SimplePolygon import SimplePolygon
from meshexchange.Surface.Extent import Extent
from shapely import Polygon


class ModelCutter:
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst
        self.main_polygon = None
        # @todo: this prefix should be retrived from the self.src
        self.path_prefix = r'\3dtiles\1'

    @staticmethod
    def download_file(uri, file_name):
        mp3file = urllib.request.urlopen(uri)
        with open(file_name, 'wb') as output:
            output.write(mp3file.read())

    @staticmethod
    def cut_download_file(uri, file_name, polygon):
        r = requests.post('http://localhost:8001/cutter/cut',
                          json={"uri": uri, 'polygon': polygon})
        with open(file_name, 'wb') as output:
            output.write(r.content)

    def processTile(self, data):

        output_directory = str(data['src'].parent).replace(self.path_prefix, self.dst).replace('\\', '/')
        osgb_dir = pathlib.Path(output_directory)
        if not osgb_dir.exists():
            osgb_dir.mkdir(parents=True, exist_ok=True)
        file_name = output_directory + '/' + str(data['src'].name)
        uri = str(data['src']).replace(self.path_prefix, self.src).replace('\\', '/')
        tile_extent = Extent.fromRad(data['extent']).transform('32636')
        tile_polygon = Polygon(tile_extent.asPolygon())
        relation = self.main_polygon.relation(tile_polygon)

        if relation == 0:  # outside
            return False, False
        elif relation == 1:  # no completely inside
            ModelCutter.cut_download_file(uri, file_name, self.main_polygon.coords())
            return True, True
        elif relation == 2:  # contains
            ModelCutter.download_file(uri, file_name)
            return True, True
        else:
            print('error')
            return False, False

    def cut(self, polygon_coords):
        # @todo: verify polygon
        self.main_polygon = SimplePolygon.fromCoords(polygon_coords, '32636')
        w = FilterTileSet(self.src, self.dst)
        w.processTileSet('', 'tileset.json', self.processTile)


if __name__ == '__main__':
    mc = ModelCutter(src="http://localhost:8000/3dtiles/1",
                     dst=r"c:\temp\copy_1_v6")
    e = Extent.fromRad([0.60086160219568729435, 0.54983752779672290245, 0.603998299633716762, 0.55182430814541350017])
    extent_utm = e.transform('32636')
    center = extent_utm.centroid()
    polygon = Extent.fromUtm36Dimensions(center[0], center[1], 1000, 1000).asPolygon()
    mc.cut(polygon)
    print('Done')
