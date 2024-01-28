import json
import logging
import pathlib
import time
from multiprocessing import Process, Queue
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
        self.src_uri = urlparse(src)
        self.ti = TileIndex(32636)
        self.w = FilterTileSet(self.src_uri.geturl(), self.dst)
        self.w.main_polygon = None
        self.indexQueue = Queue()
        self.output_file = r"c:\temp\test_index_v10.gpkg"

    def tileset_reader(self):
        while True:
            msg = self.w.tilesetQueue.get()
            if msg == "DONE":
                break
            # print('tileset:')
            # print(msg)

    def tile_reader(self):
        while True:
            msg = self.w.tileQueue.get()
            if msg == "DONE":
                break
            # print('tile:')
            # print(msg)
            self.print_tile(msg)
            # self.performConvert(msg)

    def index_writer(self):
        while True:
            msg = self.indexQueue.get()
            if msg == "SAVE":
                self.ti.export_to_geopackage(self.output_file)
                continue
            elif msg == "WAIT":
                time.sleep(10)
                continue
            elif msg == "DONE":
                break
            self.ti.append(msg['uri'], msg['coords'], density=msg['density'], level=msg['level'])

    def print_tile(self, data):
        # print(data)
        # return True, True
        output_directory = str(data['src'].parent).replace(self.src_uri.path.replace('/', '\\'), self.dst).replace('\\',
                                                                                                                   '/')
        osgb_dir = pathlib.Path(output_directory)
        if not osgb_dir.exists():
            osgb_dir.mkdir(parents=True, exist_ok=True)
        file_name = output_directory + '/' + str(data['src'].name)
        uri = str(data['src']).replace(self.src_uri.path.replace('/', '\\'), self.src_uri.geturl()).replace('\\', '/')
        tile_extent = Extent.fromRad(data['extent']).transform('32636')
        tile_polygon = Polygon(tile_extent.asPolygon())
        relation = data['relation']

        if relation == 0:
            pass
        elif relation == 2 or relation == 1:
            b = B3DMModule()
            r = requests.get(uri)
            if r.status_code == 200:
                # print('IN', uri)
                ee = b.b3dmPayloadToExtendedExchange(bytearray(r.content), Y_UP=True)
                num = ee.calculateNumberOfVertices()
                exact_extent = True
                if exact_extent:
                    sp = Splitter(ee)
                    ext = sp.ee_utm.calculateExtent()
                    extent = Extent(ext[0][0], ext[0][1], ext[1][0], ext[1][1], '32636')
                    # pol = sp.ee_utm.simple_convex_hull()
                    # coords = pol.exterior.coords
                    coords = extent.asPolygon()
                else:
                    coords = tile_extent.asPolygon()
                density = num / tile_extent.getArea()

                self.indexQueue.put({'uri': uri, 'coords': coords, 'density': density, 'level': data['level']})

            # ModelPrinter.download_file(uri, file_name)
            # b = B3DMModule()
            # ee = b.b3dmToExtendedExchange(file_name, self.dst + '/image.jpg', 'image.jpg', 0)
            #
            # b.extendedExchangeTob3dm(ee, file_name.replace('.b3dm', ''))

    @staticmethod
    def download_file(uri, file_name):
        mp3file = urllib.request.urlopen(uri)
        with open(file_name, 'wb') as output:
            output.write(mp3file.read())

    def save_tileset(self, data):
        tileset, output_tileset = data['tileset'], data['path']
        with open(output_tileset, 'w') as f:
            json.dump(tileset, f)

    def process_tileset(self, root_dir='', tileset_name='tileset.json', polygon_coords=None):
        if polygon_coords is None:
            self.w.main_polygon = None
        else:
            # @todo: verify polygon
            self.w.main_polygon = SimplePolygon.fromCoords(polygon_coords, '32636')

        self.w.processTileSet(root_dir, tileset_name)

    def startConverters(self, num_of_reader_procs, num_of_reader_procs2):
        all_reader_procs = list()
        for ii in range(0, num_of_reader_procs):
            reader_p = Process(target=self.tile_reader)
            reader_p.daemon = True
            reader_p.start()

            all_reader_procs.append(reader_p)

        for ii in range(0, num_of_reader_procs2):
            reader_p = Process(target=self.tileset_reader)
            reader_p.daemon = True
            reader_p.start()

            all_reader_procs.append(reader_p)

        reader_p = Process(target=self.index_writer)
        reader_p.daemon = True
        reader_p.start()
        all_reader_procs.append(reader_p)
        return all_reader_procs

    def stopConverters(self, num_of_reader_procs, num_of_reader_procs2):
        for ii in range(0, num_of_reader_procs):
            self.w.tileQueue.put("DONE")
        for ii in range(0, num_of_reader_procs2):
            self.w.tilesetQueue.put("DONE")

        while not self.w.tilesetQueue.empty():
            print('\r',
                  f'No more new tilesets. Converting tilesets in queue... {self.w.tilesetQueue.qsize()} tilesets left',
                  end='')
            time.sleep(1)

        print('\r', f'No more new tiles. Converting tiles in queue... {self.w.tileQueue.qsize()} tiles left', end='')
        while not self.w.tileQueue.empty():
            print('\r', f'No more new tiles. Converting tiles in queue... {self.w.tileQueue.qsize()} tiles left',
                  end='')
            time.sleep(1)
        self.indexQueue.put("SAVE")
        self.indexQueue.put("WAIT")
        self.indexQueue.put("DONE")
        while self.indexQueue.qsize()>0:
            print('\r', f'Writing index file...{self.indexQueue.qsize()}', end='')
            time.sleep(1)
        print()


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
    mc.startConverters(2, 1)
    mc.process_tileset('', 'tileset.json', polygon)
    mc.stopConverters(2, 1)

    print('Done')
